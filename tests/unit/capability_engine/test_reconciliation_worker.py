"""Tests for CapabilityReconciliationWorker -- Sprint-11. Wave-6.

Covers:
- orphan detection
- replay invocation
- score rebuild
"""

import pytest
from datetime import datetime

from karsa.capability_engine.application.capability_projection_service import (
    CapabilityProjectionService,
)
from karsa.capability_engine.application.capability_scoring_service import (
    CapabilityScoringService,
)
from karsa.capability_engine.domain.aggregates.capability_evolution import (
    CapabilityEvolution,
)
from karsa.capability_engine.domain.aggregates.capability_health_score import (
    CapabilityHealthScore,
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
    InMemoryOutboxRepository,
)
from karsa.capability_engine.workers.capability_reconciliation_worker import (
    CapabilityReconciliationWorker,
    ReconciliationResult,
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


def _make_reconciliation_env():
    evo_repo = InMemoryCapabilityEvolutionRepository()
    reg = InMemoryEvolutionVersionRegistryRepository()
    hs_repo = InMemoryCapabilityHealthScoreRepository()
    hist_repo = InMemoryScoreHistoryRepository()
    evo_proj = InMemoryEvolutionProjectionRepository()
    health_proj = InMemoryHealthProjectionRepository()
    ts_proj = InMemoryScoreTimeseriesProjectionRepository()
    outbox_repo = InMemoryOutboxRepository()

    proj_service = CapabilityProjectionService(
        evolution_repo=evo_repo,
        version_registry=reg,
        health_score_repo=hs_repo,
        score_history_repo=hist_repo,
        evolution_projection_repo=evo_proj,
        health_projection_repo=health_proj,
        timeseries_projection_repo=ts_proj,
    )
    scoring_service = CapabilityScoringService(
        health_score_repo=hs_repo,
        score_history_repo=hist_repo,
        outbox_repo=outbox_repo,
    )

    worker = CapabilityReconciliationWorker(
        evolution_repo=evo_repo,
        health_score_repo=hs_repo,
        score_history_repo=hist_repo,
        projection_service=proj_service,
        scoring_service=scoring_service,
    )
    return worker, evo_repo, hs_repo, hist_repo, proj_service, scoring_service


class TestOrphanDetection:
    """Detect evolutions with no health score."""

    def test_orphaned_evolution_detected(self):
        worker, evo_repo, hs_repo, *_ = _make_reconciliation_env()

        # Evolution exists but no health score
        evo = _make_evolution()
        evo_repo.save(evo)

        orphaned = worker.detect_orphaned_evolutions()
        assert "family-001" in orphaned

    def test_no_orphan_when_health_score_exists(self):
        worker, evo_repo, hs_repo, *_ = _make_reconciliation_env()

        evo = _make_evolution()
        evo_repo.save(evo)
        hs_repo.save(CapabilityHealthScore(
            health_score_id="hs-001",
            capability_family_id="family-001",
        ))

        orphaned = worker.detect_orphaned_evolutions()
        assert len(orphaned) == 0

    def test_multiple_families(self):
        worker, evo_repo, hs_repo, *_ = _make_reconciliation_env()

        evo1 = _make_evolution(evolution_id="evo-001", capability_family_id="f-001")
        evo2 = _make_evolution(evolution_id="evo-002", capability_family_id="f-002",
                               evaluation_id="eval-002")
        evo_repo.save(evo1)
        evo_repo.save(evo2)

        # Only f-001 has health score
        hs_repo.save(CapabilityHealthScore(
            health_score_id="hs-001",
            capability_family_id="f-001",
        ))

        orphaned = worker.detect_orphaned_evolutions()
        assert orphaned == ["f-002"]


class TestMissingHistory:
    """Detect health scores with no score history."""

    def test_missing_history_detected(self):
        worker, _, hs_repo, hist_repo, *_ = _make_reconciliation_env()

        hs_repo.save(CapabilityHealthScore(
            health_score_id="hs-001",
            capability_family_id="family-001",
        ))

        missing = worker.detect_missing_history()
        assert "family-001" in missing

    def test_no_missing_when_history_exists(self):
        worker, _, hs_repo, hist_repo, *_ = _make_reconciliation_env()

        hs_repo.save(CapabilityHealthScore(
            health_score_id="hs-001",
            capability_family_id="family-001",
        ))
        hist_repo.append(ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-001",
            evaluation_sequence=1,
            capability_version_id="ver-001",
            score=0.6,
            algorithm_version="v1.0",
        ))

        missing = worker.detect_missing_history()
        assert len(missing) == 0


class TestStaleProjectionDetection:
    """Detect projections that are stale."""

    def test_stale_when_projection_missing(self):
        worker, _, hs_repo, _, proj_service, *_ = _make_reconciliation_env()

        hs_repo.save(CapabilityHealthScore(
            health_score_id="hs-001",
            capability_family_id="family-001",
            evaluation_count=5,
        ))

        stale = worker.detect_stale_projections()
        assert "family-001" in stale

    def test_not_stale_when_projection_exists(self):
        worker, _, hs_repo, _, proj_service, *_ = _make_reconciliation_env()

        hs_repo.save(CapabilityHealthScore(
            health_score_id="hs-001",
            capability_family_id="family-001",
            evaluation_count=5,
        ))

        # Rebuild projection
        proj_service.rebuild_health_projection()

        stale = worker.detect_stale_projections()
        assert len(stale) == 0


class TestReconciliation:
    """Full reconciliation cycle."""

    def test_reconcile_returns_result(self):
        worker, *_ = _make_reconciliation_env()
        result = worker.reconcile()

        assert isinstance(result, ReconciliationResult)
        assert isinstance(result.orphaned_evolutions, list)
        assert isinstance(result.stale_projections, list)
        assert isinstance(result.missing_history, list)

    def test_reconcile_triggers_rebuild_for_stale(self):
        worker, _, hs_repo, _, _, *_ = _make_reconciliation_env()

        hs_repo.save(CapabilityHealthScore(
            health_score_id="hs-001",
            capability_family_id="family-001",
            evaluation_count=5,
        ))

        result = worker.reconcile()
        # Stale projection should trigger rebuild
        assert len(result.rebuild_results) > 0

    def test_reconcile_no_action_when_consistent(self):
        worker, evo_repo, hs_repo, hist_repo, proj_service, *_ = _make_reconciliation_env()

        # Everything consistent
        evo = _make_evolution()
        evo_repo.save(evo)
        hs_repo.save(CapabilityHealthScore(
            health_score_id="hs-001",
            capability_family_id="family-001",
            evaluation_count=1,
        ))
        hist_repo.append(ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-001",
            evaluation_sequence=1,
            capability_version_id="ver-001",
            score=0.6,
            algorithm_version="v1.0",
        ))
        proj_service.rebuild_health_projection()

        result = worker.reconcile()
        assert len(result.orphaned_evolutions) == 0
        assert len(result.missing_history) == 0
        assert len(result.stale_projections) == 0
