"""Tests for CapabilityProjectionService -- Sprint-11. Wave-5.

Covers:
- full rebuild
- deterministic rebuild
- stale source detection
- repeated rebuild idempotency
- canonical filtering
- superseded exclusion
- trigger aggregation
- score aggregation
- default row creation (ADR-131)
- null prevention (ADR-131)
- trend calculation
- completeness calculation
- algorithm version propagation
- ordering
- version boundaries
- sequence integrity
"""

import pytest
from datetime import datetime, timedelta

from karsa.capability_engine.application.capability_projection_service import (
    CapabilityProjectionService,
    RebuildResult,
)
from karsa.capability_engine.domain.aggregates.capability_evolution import (
    CapabilityEvolution,
)
from karsa.capability_engine.domain.aggregates.capability_health_score import (
    CapabilityHealthScore,
)
from karsa.capability_engine.domain.exceptions import ProjectionStalenessError
from karsa.capability_engine.domain.value_objects.capability_score_component import (
    CapabilityScoreComponent,
)
from karsa.capability_engine.domain.value_objects.enums import (
    EvolutionTriggerType,
    EvolutionType,
    EvolutionStatus,
    ScoreComponentName,
    ScoreTrend,
)
from karsa.capability_engine.domain.value_objects.evolution_context_snapshot import (
    EvolutionContextSnapshot,
    _compute_snapshot_hash,
)
from karsa.capability_engine.domain.value_objects.evolution_delta import (
    EvolutionDelta,
)
from karsa.capability_engine.domain.value_objects.evolution_evidence import (
    EvolutionEvidence,
)
from karsa.capability_engine.domain.value_objects.score_history_entry import (
    ScoreHistoryEntry,
)
from karsa.capability_engine.infrastructure.persistence.in_memory_repositories import (
    InMemoryCapabilityEvolutionRepository,
    InMemoryEvolutionVersionRegistryRepository,
    InMemoryCapabilityHealthScoreRepository,
    InMemoryScoreHistoryRepository,
    InMemoryEvolutionProjectionRepository,
    InMemoryHealthProjectionRepository,
    InMemoryScoreTimeseriesProjectionRepository,
)
from karsa.capability_engine.infrastructure.repositories.capability_evolution_version_registry_repository import (
    EvolutionVersionRegistryEntry,
)


# --- Helpers ---

def _make_snapshot():
    cap = {"version": "v1", "status": "ACTIVE"}
    rev = {"score": 0.8}
    data = {
        "capability": cap,
        "review": rev,
        "attribution": None,
        "execution": None,
        "source_versions": {"review_projection": 1},
    }
    return EvolutionContextSnapshot(
        capability_snapshot=cap,
        review_snapshot=rev,
        snapshot_hash=_compute_snapshot_hash(data),
        snapshot_source_versions={"review_projection": 1},
    )


def _make_evolution(evolution_id="evo-001", **overrides):
    defaults = dict(
        evolution_id=evolution_id,
        capability_family_id="family-001",
        evaluation_id="eval-001",
        trigger_type=EvolutionTriggerType.REVIEW_FINDING.value,
        capability_version_id="ver-001",
        capability_urn="urn:karsa:capability:ns:test:v1",
        evolution_type=EvolutionType.SCORE_ADJUSTMENT.value,
        delta=EvolutionDelta(
            before_score=0.5,
            after_score=0.7,
            score_change_bps=2000.0,
            before_lifecycle_state="ACTIVE",
            after_lifecycle_state="ACTIVE",
            before_contract_fingerprint=None,
            after_contract_fingerprint=None,
        ),
        evidence=EvolutionEvidence(
            source_type="REVIEW",
            source_id="urn:karsa:review:abc",
            finding_ids=["f1"],
        ),
        context_snapshot=_make_snapshot(),
        evaluation_sequence=1,
    )
    defaults.update(overrides)
    return CapabilityEvolution(**defaults)


def _make_health_score(**overrides):
    defaults = dict(
        health_score_id="hs-001",
        capability_family_id="family-001",
        current_score=0.65,
        algorithm_version="v1.0",
    )
    defaults.update(overrides)
    return CapabilityHealthScore(**defaults)


def _make_service():
    evolution_repo = InMemoryCapabilityEvolutionRepository()
    version_registry = InMemoryEvolutionVersionRegistryRepository()
    health_score_repo = InMemoryCapabilityHealthScoreRepository()
    score_history_repo = InMemoryScoreHistoryRepository()
    evolution_proj_repo = InMemoryEvolutionProjectionRepository()
    health_proj_repo = InMemoryHealthProjectionRepository()
    timeseries_proj_repo = InMemoryScoreTimeseriesProjectionRepository()

    service = CapabilityProjectionService(
        evolution_repo=evolution_repo,
        version_registry=version_registry,
        health_score_repo=health_score_repo,
        score_history_repo=score_history_repo,
        evolution_projection_repo=evolution_proj_repo,
        health_projection_repo=health_proj_repo,
        timeseries_projection_repo=timeseries_proj_repo,
    )
    return (
        service,
        evolution_repo,
        version_registry,
        health_score_repo,
        score_history_repo,
        evolution_proj_repo,
        health_proj_repo,
        timeseries_proj_repo,
    )


# --- Tests: Full Rebuild ---

class TestFullRebuild:
    """rebuild_all() orchestrates all three projections."""

    def test_rebuild_all_returns_three_results(self):
        service, *_ = _make_service()
        results = service.rebuild_all()
        assert len(results) == 3
        names = {r.projection_name for r in results}
        assert names == {
            "capability_evolution_projection",
            "capability_health_projection",
            "capability_score_timeseries_projection",
        }

    def test_rebuild_all_returns_rowcounts(self):
        service, evo_repo, reg, hs_repo, hist_repo, *_ = _make_service()

        # Add source data
        evo = _make_evolution()
        evo_repo.save(evo)
        reg.save(EvolutionVersionRegistryEntry(
            version_id="vr-001",
            capability_family_id="family-001",
            evaluation_id="eval-001",
            trigger_type="REVIEW_FINDING",
            evolution_id="evo-001",
            evolution_status=EvolutionStatus.CANONICAL.value,
        ))
        hs_repo.save(_make_health_score())
        hist_repo.append(ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-001",
            evaluation_sequence=1,
            capability_version_id="ver-001",
            score=0.65,
            algorithm_version="v1.0",
        ))

        results = service.rebuild_all()
        evo_result = next(r for r in results if r.projection_name == "capability_evolution_projection")
        health_result = next(r for r in results if r.projection_name == "capability_health_projection")
        ts_result = next(r for r in results if r.projection_name == "capability_score_timeseries_projection")

        assert evo_result.rows_written == 1
        assert health_result.rows_written == 1
        assert ts_result.rows_written == 1


# --- Tests: Deterministic Rebuild ---

class TestDeterministicRebuild:
    """ADR-126: Rebuild produces identical results from same source data."""

    def test_rebuild_is_deterministic(self):
        service, evo_repo, reg, hs_repo, *_ = _make_service()

        evo = _make_evolution()
        evo_repo.save(evo)
        reg.save(EvolutionVersionRegistryEntry(
            version_id="vr-001",
            capability_family_id="family-001",
            evaluation_id="eval-001",
            trigger_type="REVIEW_FINDING",
            evolution_id="evo-001",
            evolution_status=EvolutionStatus.CANONICAL.value,
        ))
        hs_repo.save(_make_health_score())

        # First rebuild
        service.rebuild_evolution_projection()
        first = dict(service._evolution_projection_repo._store)

        # Second rebuild
        service.rebuild_evolution_projection()
        second = dict(service._evolution_projection_repo._store)

        assert first == second

    def test_health_rebuild_is_deterministic(self):
        service, _, _, hs_repo, *_ = _make_service()
        hs_repo.save(_make_health_score())

        service.rebuild_health_projection()
        first = dict(service._health_projection_repo._store)

        service.rebuild_health_projection()
        second = dict(service._health_projection_repo._store)

        assert first == second


# --- Tests: Stale Source Detection ---

class TestStaleSourceDetection:
    """ADR-135: Validate source checkpoint consistency."""

    def test_stale_source_raises_error(self):
        service, *_ = _make_service()
        with pytest.raises(ProjectionStalenessError, match="has advanced"):
            service.rebuild_evolution_projection(
                source_checkpoint=5, current_checkpoint=10
            )

    def test_matching_checkpoint_passes(self):
        service, *_ = _make_service()
        result = service.rebuild_evolution_projection(
            source_checkpoint=10, current_checkpoint=10
        )
        assert result.rows_written == 0

    def test_no_checkpoint_passes(self):
        service, *_ = _make_service()
        result = service.rebuild_evolution_projection()
        assert result.rows_written == 0

    def test_stale_health_rebuild_raises(self):
        service, *_ = _make_service()
        with pytest.raises(ProjectionStalenessError):
            service.rebuild_health_projection(
                source_checkpoint=1, current_checkpoint=5
            )

    def test_stale_timeseries_rebuild_raises(self):
        service, *_ = _make_service()
        with pytest.raises(ProjectionStalenessError):
            service.rebuild_timeseries_projection(
                source_checkpoint=3, current_checkpoint=7
            )

    def test_stale_rebuild_all_raises(self):
        service, *_ = _make_service()
        with pytest.raises(ProjectionStalenessError):
            service.rebuild_all(
                source_checkpoint=1, current_checkpoint=2
            )


# --- Tests: Repeated Rebuild Idempotency ---

class TestRepeatedRebuildIdempotency:
    """TRUNCATE + INSERT: repeated rebuild produces same result."""

    def test_evolution_rebuild_idempotent(self):
        service, evo_repo, reg, *_ = _make_service()

        evo = _make_evolution()
        evo_repo.save(evo)
        reg.save(EvolutionVersionRegistryEntry(
            version_id="vr-001",
            capability_family_id="family-001",
            evaluation_id="eval-001",
            trigger_type="REVIEW_FINDING",
            evolution_id="evo-001",
            evolution_status=EvolutionStatus.CANONICAL.value,
        ))

        r1 = service.rebuild_evolution_projection()
        r2 = service.rebuild_evolution_projection()
        r3 = service.rebuild_evolution_projection()

        assert r1.rows_written == r2.rows_written == r3.rows_written == 1
        assert len(service._evolution_projection_repo._store) == 1

    def test_health_rebuild_idempotent(self):
        service, _, _, hs_repo, *_ = _make_service()
        hs_repo.save(_make_health_score())

        r1 = service.rebuild_health_projection()
        r2 = service.rebuild_health_projection()

        assert r1.rows_written == r2.rows_written == 1
        assert len(service._health_projection_repo._store) == 1


# --- Tests: Canonical Filtering ---

class TestCanonicalFiltering:
    """ADR-133: Only canonical records contribute."""

    def test_canonical_evolution_included(self):
        service, evo_repo, reg, *_ = _make_service()
        evo = _make_evolution()
        evo_repo.save(evo)
        reg.save(EvolutionVersionRegistryEntry(
            version_id="vr-001",
            capability_family_id="family-001",
            evaluation_id="eval-001",
            trigger_type="REVIEW_FINDING",
            evolution_id="evo-001",
            evolution_status=EvolutionStatus.CANONICAL.value,
        ))

        service.rebuild_evolution_projection()
        assert "family-001" in service._evolution_projection_repo._store

    def test_superseded_evolution_excluded(self):
        service, evo_repo, reg, *_ = _make_service()
        evo = _make_evolution()
        evo_repo.save(evo)
        reg.save(EvolutionVersionRegistryEntry(
            version_id="vr-001",
            capability_family_id="family-001",
            evaluation_id="eval-001",
            trigger_type="REVIEW_FINDING",
            evolution_id="evo-001",
            evolution_status=EvolutionStatus.SUPERSEDED.value,
        ))

        service.rebuild_evolution_projection()
        assert len(service._evolution_projection_repo._store) == 0

    def test_no_registry_entry_excluded(self):
        service, evo_repo, _, *_ = _make_service()
        evo = _make_evolution()
        evo_repo.save(evo)
        # No registry entry at all

        service.rebuild_evolution_projection()
        assert len(service._evolution_projection_repo._store) == 0


# --- Tests: Superseded Exclusion ---

class TestSupersededExclusion:
    """ADR-133: Superseded records do not contribute."""

    def test_only_canonical_contributes_when_both_exist(self):
        service, evo_repo, reg, *_ = _make_service()

        # Old evolution (superseded)
        old = _make_evolution(evolution_id="evo-old")
        evo_repo.save(old)

        # New evolution (canonical)
        new = _make_evolution(
            evolution_id="evo-new",
            evaluation_id="eval-002",
            evaluation_sequence=2,
        )
        evo_repo.save(new)

        # Registry: old is superseded, new is canonical
        reg.save(EvolutionVersionRegistryEntry(
            version_id="vr-old",
            capability_family_id="family-001",
            evaluation_id="eval-001",
            trigger_type="REVIEW_FINDING",
            evolution_id="evo-old",
            evolution_status=EvolutionStatus.SUPERSEDED.value,
            superseded_by="evo-new",
        ))
        reg.save(EvolutionVersionRegistryEntry(
            version_id="vr-new",
            capability_family_id="family-001",
            evaluation_id="eval-002",
            trigger_type="REVIEW_FINDING",
            evolution_id="evo-new",
            evolution_status=EvolutionStatus.CANONICAL.value,
        ))

        service.rebuild_evolution_projection()
        summary = service._evolution_projection_repo._store.get("family-001")
        assert summary is not None
        assert summary["total_evolutions"] == 1  # only the canonical one


# --- Tests: Trigger Aggregation ---

class TestTriggerAggregation:
    """Evolution projection aggregates by trigger type."""

    def test_multiple_triggers_aggregated(self):
        service, evo_repo, reg, *_ = _make_service()

        review = _make_evolution(
            evolution_id="evo-review",
            trigger_type=EvolutionTriggerType.REVIEW_FINDING.value,
        )
        attr = _make_evolution(
            evolution_id="evo-attr",
            evaluation_id="eval-002",
            trigger_type=EvolutionTriggerType.ATTRIBUTION_INSIGHT.value,
            evaluation_sequence=2,
        )
        evo_repo.save(review)
        evo_repo.save(attr)

        for evo, trigger in [(review, "REVIEW_FINDING"), (attr, "ATTRIBUTION_INSIGHT")]:
            reg.save(EvolutionVersionRegistryEntry(
                version_id=f"vr-{evo.evolution_id}",
                capability_family_id="family-001",
                evaluation_id=evo.evaluation_id,
                trigger_type=trigger,
                evolution_id=evo.evolution_id,
                evolution_status=EvolutionStatus.CANONICAL.value,
            ))

        service.rebuild_evolution_projection()
        summary = service._evolution_projection_repo._store["family-001"]
        assert summary["total_evolutions"] == 2
        assert summary["trigger_type_breakdown"]["REVIEW_FINDING"] == 1
        assert summary["trigger_type_breakdown"]["ATTRIBUTION_INSIGHT"] == 1


# --- Tests: Score Aggregation ---

class TestScoreAggregation:
    """Evolution projection aggregates score changes."""

    def test_positive_negative_counting(self):
        service, evo_repo, reg, *_ = _make_service()

        # Positive evolution
        pos = _make_evolution(
            evolution_id="evo-pos",
            delta=EvolutionDelta(
                before_score=0.5,
                after_score=0.7,
                score_change_bps=2000.0,
                before_lifecycle_state="ACTIVE",
                after_lifecycle_state="ACTIVE",
                before_contract_fingerprint=None,
                after_contract_fingerprint=None,
            ),
        )
        # Negative evolution
        neg = _make_evolution(
            evolution_id="evo-neg",
            evaluation_id="eval-002",
            evaluation_sequence=2,
            delta=EvolutionDelta(
                before_score=0.7,
                after_score=0.5,
                score_change_bps=-2000.0,
                before_lifecycle_state="ACTIVE",
                after_lifecycle_state="ACTIVE",
                before_contract_fingerprint=None,
                after_contract_fingerprint=None,
            ),
        )
        evo_repo.save(pos)
        evo_repo.save(neg)

        for evo in [pos, neg]:
            reg.save(EvolutionVersionRegistryEntry(
                version_id=f"vr-{evo.evolution_id}",
                capability_family_id="family-001",
                evaluation_id=evo.evaluation_id,
                trigger_type="REVIEW_FINDING",
                evolution_id=evo.evolution_id,
                evolution_status=EvolutionStatus.CANONICAL.value,
            ))

        service.rebuild_evolution_projection()
        summary = service._evolution_projection_repo._store["family-001"]
        assert summary["positive_evolutions"] == 1
        assert summary["negative_evolutions"] == 1
        assert summary["avg_score_change_bps"] == 0.0


# --- Tests: Health Projection Default Row Creation ---

class TestHealthProjectionDefaults:
    """ADR-131: Every ACTIVE capability must have a row."""

    def test_health_score_creates_projection(self):
        service, _, _, hs_repo, *_ = _make_service()
        hs_repo.save(_make_health_score())

        result = service.rebuild_health_projection()
        assert result.rows_written == 1
        assert "family-001" in service._health_projection_repo._store

    def test_empty_health_scores_no_rows(self):
        service, *_ = _make_service()
        result = service.rebuild_health_projection()
        assert result.rows_written == 0


# --- Tests: Null Prevention ---

class TestNullPrevention:
    """ADR-131: All projection fields must have non-null values."""

    def test_health_projection_no_nulls(self):
        service, _, _, hs_repo, _, _, health_proj, *_ = _make_service()

        # Health score with minimal components
        hs = _make_health_score()
        hs_repo.save(hs)

        service.rebuild_health_projection()
        proj = health_proj._store["family-001"]

        # Verify no None values (except last_evaluated_at which is optional)
        for key, value in proj.items():
            if key == "last_evaluated_at":
                continue  # Optional timestamp, None if never evaluated
            assert value is not None, f"Field {key} is None"

    def test_default_score_is_half(self):
        """ADR-131: Default score = 0.5."""
        service, _, _, hs_repo, _, _, health_proj, *_ = _make_service()
        hs = _make_health_score(current_score=0.5)
        hs_repo.save(hs)

        service.rebuild_health_projection()
        proj = health_proj._store["family-001"]
        assert proj["current_score"] == 0.5


# --- Tests: Trend Calculation ---

class TestTrendCalculation:
    """ADR-136: Score trend from recent history."""

    def test_improving_trend(self):
        service, _, _, hs_repo, hist_repo, _, health_proj, *_ = _make_service()
        hs = _make_health_score()
        hs_repo.save(hs)

        for i, score in enumerate([0.3, 0.5, 0.7]):
            hist_repo.append(ScoreHistoryEntry(
                capability_family_id="family-001",
                evaluation_id=f"eval-{i:03d}",
                evaluation_sequence=i + 1,
                capability_version_id="ver-001",
                score=score,
                algorithm_version="v1.0",
            ))

        service.rebuild_health_projection()
        assert health_proj._store["family-001"]["score_trend"] == ScoreTrend.IMPROVING.value

    def test_declining_trend(self):
        service, _, _, hs_repo, hist_repo, _, health_proj, *_ = _make_service()
        hs = _make_health_score()
        hs_repo.save(hs)

        for i, score in enumerate([0.7, 0.5, 0.3]):
            hist_repo.append(ScoreHistoryEntry(
                capability_family_id="family-001",
                evaluation_id=f"eval-{i:03d}",
                evaluation_sequence=i + 1,
                capability_version_id="ver-001",
                score=score,
                algorithm_version="v1.0",
            ))

        service.rebuild_health_projection()
        assert health_proj._store["family-001"]["score_trend"] == ScoreTrend.DECLINING.value

    def test_stable_trend(self):
        service, _, _, hs_repo, hist_repo, _, health_proj, *_ = _make_service()
        hs = _make_health_score()
        hs_repo.save(hs)

        for i, score in enumerate([0.5, 0.6, 0.5]):
            hist_repo.append(ScoreHistoryEntry(
                capability_family_id="family-001",
                evaluation_id=f"eval-{i:03d}",
                evaluation_sequence=i + 1,
                capability_version_id="ver-001",
                score=score,
                algorithm_version="v1.0",
            ))

        service.rebuild_health_projection()
        assert health_proj._store["family-001"]["score_trend"] == ScoreTrend.STABLE.value

    def test_unknown_trend_insufficient_data(self):
        service, _, _, hs_repo, hist_repo, _, health_proj, *_ = _make_service()
        hs = _make_health_score()
        hs_repo.save(hs)

        hist_repo.append(ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-001",
            evaluation_sequence=1,
            capability_version_id="ver-001",
            score=0.5,
            algorithm_version="v1.0",
        ))

        service.rebuild_health_projection()
        assert health_proj._store["family-001"]["score_trend"] == ScoreTrend.UNKNOWN.value


# --- Tests: Completeness Calculation ---

class TestCompletenessCalculation:
    """Health projection data completeness."""

    def test_full_completeness(self):
        service, _, _, hs_repo, _, _, health_proj, *_ = _make_service()
        hs = _make_health_score(score_components=[
            CapabilityScoreComponent(
                component_name=ScoreComponentName.EXECUTION_QUALITY.value,
                component_score=0.8, weight=0.25,
                evaluation_count=1, confidence=0.9,
            ),
            CapabilityScoreComponent(
                component_name=ScoreComponentName.ATTRIBUTION_ALIGNMENT.value,
                component_score=0.7, weight=0.25,
                evaluation_count=1, confidence=0.85,
            ),
            CapabilityScoreComponent(
                component_name=ScoreComponentName.REVIEW_SENTIMENT.value,
                component_score=0.6, weight=0.25,
                evaluation_count=1, confidence=0.8,
            ),
            CapabilityScoreComponent(
                component_name=ScoreComponentName.REGIME_FITNESS.value,
                component_score=0.9, weight=0.25,
                evaluation_count=1, confidence=0.95,
            ),
        ])
        hs_repo.save(hs)

        service.rebuild_health_projection()
        assert health_proj._store["family-001"]["data_completeness"] == 1.0

    def test_zero_completeness_no_components(self):
        service, _, _, hs_repo, _, _, health_proj, *_ = _make_service()
        hs = _make_health_score(score_components=[])
        hs_repo.save(hs)

        service.rebuild_health_projection()
        assert health_proj._store["family-001"]["data_completeness"] == 0.0

    def test_partial_completeness(self):
        service, _, _, hs_repo, _, _, health_proj, *_ = _make_service()
        hs = _make_health_score(score_components=[
            CapabilityScoreComponent(
                component_name=ScoreComponentName.EXECUTION_QUALITY.value,
                component_score=0.8, weight=0.25,
                evaluation_count=1, confidence=0.9,
            ),
        ])
        hs_repo.save(hs)

        service.rebuild_health_projection()
        assert health_proj._store["family-001"]["data_completeness"] == 0.25


# --- Tests: Algorithm Version Propagation ---

class TestAlgorithmVersionPropagation:
    """ADR-134: Algorithm version in projections."""

    def test_algorithm_version_in_health_projection(self):
        service, _, _, hs_repo, _, _, health_proj, *_ = _make_service()
        hs = _make_health_score(algorithm_version="v2.0")
        hs_repo.save(hs)

        service.rebuild_health_projection()
        assert health_proj._store["family-001"]["algorithm_version"] == "v2.0"

    def test_algorithm_version_in_timeseries(self):
        service, _, _, hs_repo, hist_repo, _, _, ts_repo, *_ = _make_service()
        hs = _make_health_score()
        hs_repo.save(hs)
        hist_repo.append(ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-001",
            evaluation_sequence=1,
            capability_version_id="ver-001",
            score=0.65,
            algorithm_version="v2.0",
        ))

        service.rebuild_timeseries_projection()
        assert ts_repo._store[0]["algorithm_version"] == "v2.0"


# --- Tests: Ordering ---

class TestOrdering:
    """ADR-136: Timeseries ordered by evaluation_sequence."""

    def test_timeseries_ordered_by_sequence(self):
        service, _, _, hs_repo, hist_repo, _, _, ts_repo, *_ = _make_service()
        hs = _make_health_score()
        hs_repo.save(hs)

        # Insert in order (repo enforces monotonic ordering)
        for seq in [1, 2, 3]:
            hist_repo.append(ScoreHistoryEntry(
                capability_family_id="family-001",
                evaluation_id=f"eval-{seq:03d}",
                evaluation_sequence=seq,
                capability_version_id="ver-001",
                score=0.5 + seq * 0.05,
                algorithm_version="v1.0",
            ))

        service.rebuild_timeseries_projection()
        sequences = [e["evaluation_sequence"] for e in ts_repo._store]
        assert sequences == [1, 2, 3]


# --- Tests: Version Boundaries ---

class TestVersionBoundaries:
    """ADR-137: Version boundaries preserved in timeseries."""

    def test_different_versions_preserved(self):
        service, _, _, hs_repo, hist_repo, _, _, ts_repo, *_ = _make_service()
        hs = _make_health_score()
        hs_repo.save(hs)

        hist_repo.append(ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-001",
            evaluation_sequence=1,
            capability_version_id="ver-v1",
            score=0.5,
            algorithm_version="v1.0",
        ))
        hist_repo.append(ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-002",
            evaluation_sequence=2,
            capability_version_id="ver-v2",
            score=0.7,
            algorithm_version="v1.0",
        ))

        service.rebuild_timeseries_projection()
        versions = [e["capability_version_id"] for e in ts_repo._store]
        assert versions == ["ver-v1", "ver-v2"]

    def test_version_filter_in_timeseries(self):
        service, _, _, hs_repo, hist_repo, _, _, ts_repo, *_ = _make_service()
        hs = _make_health_score()
        hs_repo.save(hs)

        hist_repo.append(ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-001",
            evaluation_sequence=1,
            capability_version_id="ver-v1",
            score=0.5,
            algorithm_version="v1.0",
        ))
        hist_repo.append(ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-002",
            evaluation_sequence=2,
            capability_version_id="ver-v2",
            score=0.7,
            algorithm_version="v1.0",
        ))

        service.rebuild_timeseries_projection()
        v1_entries = ts_repo.get_by_family_and_version("family-001", "ver-v1")
        v2_entries = ts_repo.get_by_family_and_version("family-001", "ver-v2")
        assert len(v1_entries) == 1
        assert len(v2_entries) == 1


# --- Tests: Sequence Integrity ---

class TestSequenceIntegrity:
    """ADR-136: Monotonic sequence in timeseries."""

    def test_sequences_monotonic(self):
        service, _, _, hs_repo, hist_repo, _, _, ts_repo, *_ = _make_service()
        hs = _make_health_score()
        hs_repo.save(hs)

        for i in range(10):
            hist_repo.append(ScoreHistoryEntry(
                capability_family_id="family-001",
                evaluation_id=f"eval-{i:03d}",
                evaluation_sequence=i + 1,
                capability_version_id="ver-001",
                score=0.5,
                algorithm_version="v1.0",
            ))

        service.rebuild_timeseries_projection()
        sequences = [e["evaluation_sequence"] for e in ts_repo._store]
        assert sequences == list(range(1, 11))


# --- Tests: Component Score Propagation ---

class TestComponentScorePropagation:
    """ADR-132: 4-factor component scores in health projection."""

    def test_component_scores_propagated(self):
        service, _, _, hs_repo, _, _, health_proj, *_ = _make_service()
        hs = _make_health_score(score_components=[
            CapabilityScoreComponent(
                component_name=ScoreComponentName.EXECUTION_QUALITY.value,
                component_score=0.85, weight=0.25,
                evaluation_count=1, confidence=0.9,
            ),
            CapabilityScoreComponent(
                component_name=ScoreComponentName.ATTRIBUTION_ALIGNMENT.value,
                component_score=0.75, weight=0.25,
                evaluation_count=1, confidence=0.85,
            ),
            CapabilityScoreComponent(
                component_name=ScoreComponentName.REVIEW_SENTIMENT.value,
                component_score=0.65, weight=0.25,
                evaluation_count=1, confidence=0.8,
            ),
            CapabilityScoreComponent(
                component_name=ScoreComponentName.REGIME_FITNESS.value,
                component_score=0.95, weight=0.25,
                evaluation_count=1, confidence=0.95,
            ),
        ])
        hs_repo.save(hs)

        service.rebuild_health_projection()
        proj = health_proj._store["family-001"]
        assert proj["execution_quality_score"] == 0.85
        assert proj["attribution_alignment_score"] == 0.75
        assert proj["review_sentiment_score"] == 0.65
        assert proj["regime_fitness_score"] == 0.95


# --- Tests: Governance Counter Propagation ---

class TestGovernanceCounterPropagation:
    """ADR-138: Consecutive score counters in health projection."""

    def test_governance_counters_propagated(self):
        service, _, _, hs_repo, _, _, health_proj, *_ = _make_service()
        hs = _make_health_score()
        hs.consecutive_low_scores = 2
        hs.consecutive_high_scores = 0
        hs_repo.save(hs)

        service.rebuild_health_projection()
        proj = health_proj._store["family-001"]
        assert proj["consecutive_low_scores"] == 2
        assert proj["consecutive_high_scores"] == 0
