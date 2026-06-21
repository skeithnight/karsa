"""Tests for CapabilityProjectionWorker -- Sprint-11. Wave-6.

Covers:
- event routing
- rebuild trigger
- stale checkpoint handling
"""

import pytest
from datetime import datetime

from karsa.capability_engine.application.capability_projection_service import (
    CapabilityProjectionService,
    RebuildResult,
)
from karsa.capability_engine.domain.aggregates.capability_health_score import (
    CapabilityHealthScore,
)
from karsa.capability_engine.domain.exceptions import ProjectionStalenessError
from karsa.capability_engine.domain.value_objects.enums import EvolutionStatus
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
from karsa.capability_engine.domain.aggregates.capability_evolution import (
    CapabilityEvolution,
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
from karsa.capability_engine.workers.capability_projection_worker import (
    CapabilityProjectionWorker,
    ProjectionWorkerResult,
)


def _make_snapshot():
    cap = {"version": "v1", "status": "ACTIVE"}
    rev = {"score": 0.8}
    data = {
        "capability": cap, "review": rev,
        "attribution": None, "execution": None,
        "source_versions": {"review_projection": 1},
    }
    return EvolutionContextSnapshot(
        capability_snapshot=cap,
        review_snapshot=rev,
        snapshot_hash=_compute_snapshot_hash(data),
        snapshot_source_versions={"review_projection": 1},
    )


def _make_evolution(**overrides):
    defaults = dict(
        evolution_id="evo-001",
        capability_family_id="family-001",
        evaluation_id="eval-001",
        trigger_type="REVIEW_FINDING",
        capability_version_id="ver-001",
        capability_urn="urn:karsa:capability:ns:test:v1",
        evolution_type="SCORE_ADJUSTMENT",
        delta=EvolutionDelta(
            before_score=0.5, after_score=0.7, score_change_bps=2000.0,
            before_lifecycle_state="ACTIVE", after_lifecycle_state="ACTIVE",
            before_contract_fingerprint=None, after_contract_fingerprint=None,
        ),
        evidence=EvolutionEvidence(
            source_type="REVIEW", source_id="urn:karsa:review:abc",
            finding_ids=["f1"],
        ),
        context_snapshot=_make_snapshot(),
        evaluation_sequence=1,
    )
    defaults.update(overrides)
    return CapabilityEvolution(**defaults)


def _make_projection_service():
    evo_repo = InMemoryCapabilityEvolutionRepository()
    reg = InMemoryEvolutionVersionRegistryRepository()
    hs_repo = InMemoryCapabilityHealthScoreRepository()
    hist_repo = InMemoryScoreHistoryRepository()
    evo_proj = InMemoryEvolutionProjectionRepository()
    health_proj = InMemoryHealthProjectionRepository()
    ts_proj = InMemoryScoreTimeseriesProjectionRepository()

    service = CapabilityProjectionService(
        evolution_repo=evo_repo,
        version_registry=reg,
        health_score_repo=hs_repo,
        score_history_repo=hist_repo,
        evolution_projection_repo=evo_proj,
        health_projection_repo=health_proj,
        timeseries_projection_repo=ts_proj,
    )
    return service, evo_repo, reg, hs_repo, hist_repo, evo_proj, health_proj, ts_proj


class TestEventRouting:
    """Worker routes events to correct rebuild methods."""

    def test_evolution_recorded_triggers_rebuild(self):
        service, evo_repo, reg, *_ = _make_projection_service()
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

        worker = CapabilityProjectionWorker(projection_service=service)
        result = worker.handle_evolution_recorded({})

        assert result is not None
        assert result.projection_name == "capability_evolution_projection"
        assert result.rows_written == 1

    def test_health_score_updated_triggers_rebuild(self):
        service, _, _, hs_repo, *_ = _make_projection_service()
        hs_repo.save(CapabilityHealthScore(
            health_score_id="hs-001",
            capability_family_id="family-001",
        ))

        worker = CapabilityProjectionWorker(projection_service=service)
        result = worker.handle_health_score_updated({})

        assert result is not None
        assert result.projection_name == "capability_health_projection"
        assert result.rows_written == 1

    def test_canonical_changed_triggers_rebuild(self):
        service, evo_repo, reg, *_ = _make_projection_service()
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

        worker = CapabilityProjectionWorker(projection_service=service)
        result = worker.handle_canonical_changed({})

        assert result is not None
        assert result.rows_written == 1


class TestRebuildTrigger:
    """Worker triggers full rebuild via rebuild_all."""

    def test_rebuild_all_returns_results(self):
        service, *_ = _make_projection_service()
        worker = CapabilityProjectionWorker(projection_service=service)
        results = worker.rebuild_all()

        assert len(results) == 3
        names = {r.projection_name for r in results}
        assert "capability_evolution_projection" in names
        assert "capability_health_projection" in names
        assert "capability_score_timeseries_projection" in names


class TestStaleCheckpointHandling:
    """ADR-135: Worker propagates ProjectionStalenessError."""

    def test_stale_checkpoint_raises_on_evolution_rebuild(self):
        service, *_ = _make_projection_service()
        worker = CapabilityProjectionWorker(
            projection_service=service,
            source_checkpoint=5,
            current_checkpoint=10,
        )

        with pytest.raises(ProjectionStalenessError):
            worker.handle_evolution_recorded({})

    def test_stale_checkpoint_raises_on_health_rebuild(self):
        service, *_ = _make_projection_service()
        worker = CapabilityProjectionWorker(
            projection_service=service,
            source_checkpoint=1,
            current_checkpoint=5,
        )

        with pytest.raises(ProjectionStalenessError):
            worker.handle_health_score_updated({})

    def test_stale_checkpoint_raises_on_canonical_changed(self):
        service, *_ = _make_projection_service()
        worker = CapabilityProjectionWorker(
            projection_service=service,
            source_checkpoint=2,
            current_checkpoint=8,
        )

        with pytest.raises(ProjectionStalenessError):
            worker.handle_canonical_changed({})

    def test_matching_checkpoint_passes(self):
        service, *_ = _make_projection_service()
        worker = CapabilityProjectionWorker(
            projection_service=service,
            source_checkpoint=10,
            current_checkpoint=10,
        )

        result = worker.handle_evolution_recorded({})
        assert result is not None
