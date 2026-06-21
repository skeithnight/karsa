"""Integration: ADR-130 Recovery -- Sprint-11. Wave-7.

Scenario 5: Transaction A succeeds, Transaction B absent.
Verify: Reconciliation detects orphan, Recovery path executes.
"""

import pytest

from karsa.capability_engine.domain.aggregates.capability_health_score import (
    CapabilityHealthScore,
)
from karsa.capability_engine.integration.capability_engine_bootstrap import bootstrap
from karsa.capability_engine.integration.capability_engine_fixture import (
    make_evolution,
    make_registry_entry,
)


@pytest.fixture
def ctx():
    return bootstrap()


class TestRecoveryFlow:
    """ADR-130: Transaction A/B split detection and recovery."""

    def test_orphaned_evolution_detected(self, ctx):
        """Evolution exists but health score missing."""
        evo = make_evolution()
        ctx.evolution_repo.save(evo)
        # No health score created

        orphaned = ctx.reconciliation_worker.detect_orphaned_evolutions()
        assert evo.capability_family_id in orphaned

    def test_no_orphan_when_both_exist(self, ctx):
        evo = make_evolution()
        ctx.evolution_repo.save(evo)
        ctx.health_score_repo.save(CapabilityHealthScore(
            health_score_id="int-hs-001",
            capability_family_id=evo.capability_family_id,
        ))

        orphaned = ctx.reconciliation_worker.detect_orphaned_evolutions()
        assert len(orphaned) == 0

    def test_missing_history_detected(self, ctx):
        ctx.health_score_repo.save(CapabilityHealthScore(
            health_score_id="int-hs-001",
            capability_family_id="int-family-001",
        ))
        # No history entries

        missing = ctx.reconciliation_worker.detect_missing_history()
        assert "int-family-001" in missing

    def test_stale_projection_detected(self, ctx):
        ctx.health_score_repo.save(CapabilityHealthScore(
            health_score_id="int-hs-001",
            capability_family_id="int-family-001",
            evaluation_count=5,
        ))
        # No projection rebuild

        stale = ctx.reconciliation_worker.detect_stale_projections()
        assert "int-family-001" in stale

    def test_reconciliation_triggers_rebuild(self, ctx):
        ctx.health_score_repo.save(CapabilityHealthScore(
            health_score_id="int-hs-001",
            capability_family_id="int-family-001",
            evaluation_count=5,
        ))

        result = ctx.reconciliation_worker.reconcile()
        assert len(result.stale_projections) > 0
        assert len(result.rebuild_results) > 0

    def test_full_recovery_flow(self, ctx):
        """Full ADR-130 recovery: orphan detected -> reconcile -> rebuild."""
        evo = make_evolution()
        ctx.evolution_repo.save(evo)
        ctx.version_registry.save(make_registry_entry(
            evolution_id=evo.evolution_id,
        ))

        # Reconciliation detects orphan
        orphaned = ctx.reconciliation_worker.detect_orphaned_evolutions()
        assert evo.capability_family_id in orphaned

        # Reconciliation triggers rebuild for stale projections
        result = ctx.reconciliation_worker.reconcile()
        assert isinstance(result.orphaned_evolutions, list)
