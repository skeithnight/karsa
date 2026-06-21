"""Tests for CapabilityCommandFacade -- Sprint-11. Wave-8.

Scenarios:
- RecordCapabilityEvolutionCommand -> CapabilityEvolutionService
- UpdateCapabilityHealthCommand -> CapabilityScoringService
- RebuildCapabilityProjectionsCommand -> ProjectionService
- ReconcileCapabilityStateCommand -> ReconciliationWorker

Verifies: No domain types leak through the facade.
"""

import pytest

from karsa.capability_engine.contracts.record_capability_evolution import (
    RecordCapabilityEvolutionCommand,
)
from karsa.capability_engine.contracts.update_capability_health import (
    UpdateCapabilityHealthCommand,
)
from karsa.capability_engine.contracts.rebuild_capability_projections import (
    RebuildCapabilityProjectionsCommand,
)
from karsa.capability_engine.contracts.reconcile_capability_state import (
    ReconcileCapabilityStateCommand,
)
from karsa.capability_engine.integration.capability_command_facade import (
    CapabilityCommandFacade,
    CommandResult,
)
from karsa.capability_engine.integration.capability_engine_bootstrap import (
    bootstrap,
)


@pytest.fixture
def facade():
    ctx = bootstrap()
    return CapabilityCommandFacade(
        evolution_service=ctx.evolution_service,
        scoring_service=ctx.scoring_service,
        projection_service=ctx.projection_service,
        reconciliation_service=ctx.reconciliation_service,
    )


class TestRecordEvolutionCommand:
    """Scenario 1+2: Review/Attribution -> Command -> Service."""

    def test_record_evolution_via_contract(self, facade):
        cmd = RecordCapabilityEvolutionCommand(
            capability_family_id="facade-family-001",
            evaluation_id="facade-eval-001",
            trigger_type="REVIEW_FINDING",
            capability_version_id="facade-ver-001",
            capability_urn="urn:karsa:capability:ns:facade-family-001:v1",
            evolution_type="SCORE_ADJUSTMENT",
            before_score=0.5,
            after_score=0.7,
            score_change_bps=2000.0,
            before_lifecycle_state="ACTIVE",
            after_lifecycle_state="ACTIVE",
            source_type="REVIEW",
            source_id="urn:karsa:review:facade-001",
            finding_ids=["f-001"],
            capability_snapshot={"version": "v1", "status": "ACTIVE"},
            review_snapshot={"score": 0.7},
            snapshot_source_versions={"review_projection": 1},
            evaluation_sequence=1,
            quality_score=0.8,
        )

        result = facade.record_evolution(cmd)

        assert result.success is True
        assert result.message == "Evolution recorded"
        assert "evolution_id" in result.data

    def test_command_result_contract(self, facade):
        cmd = RecordCapabilityEvolutionCommand(
            capability_family_id="facade-family-002",
            evaluation_id="facade-eval-002",
            trigger_type="REVIEW_FINDING",
            capability_version_id="facade-ver-002",
            capability_urn="urn:test",
            evolution_type="SCORE_ADJUSTMENT",
            before_score=0.5,
            after_score=0.7,
            score_change_bps=2000.0,
            before_lifecycle_state="ACTIVE",
            after_lifecycle_state="ACTIVE",
            source_type="REVIEW",
            source_id="urn:test",
            finding_ids=["f-001"],
            capability_snapshot={"version": "v1"},
            review_snapshot={"score": 0.7},
            snapshot_source_versions={"review_projection": 1},
            evaluation_sequence=1,
            quality_score=0.3,  # at threshold
        )

        result = facade.record_evolution(cmd)
        assert isinstance(result, CommandResult)


class TestUpdateHealthCommand:
    """Update health score via contract."""

    def test_update_health_via_contract(self, facade):
        cmd = UpdateCapabilityHealthCommand(
            capability_family_id="facade-family-003",
            evaluation_id="facade-eval-003",
            evaluation_sequence=1,
            capability_version_id="facade-ver-003",
            score=0.75,
            components=[
                {
                    "component_name": "EXECUTION_QUALITY",
                    "component_score": 0.8,
                    "weight": 0.25,
                    "evaluation_count": 1,
                    "confidence": 0.9,
                },
            ],
            algorithm_version="v1.0",
        )

        result = facade.update_health(cmd)

        assert result.success is True
        assert result.message == "Health updated"


class TestRebuildProjectionsCommand:
    """Trigger projection rebuild via contract."""

    def test_rebuild_via_contract(self, facade):
        cmd = RebuildCapabilityProjectionsCommand()

        result = facade.rebuild_projections(cmd)

        assert result.success is True
        assert "projections" in result.data
        assert len(result.data["projections"]) == 3


class TestReconcileCommand:
    """Scenario 7: Reconciliation via contract. ADR-130."""

    def test_reconcile_via_contract(self, facade):
        cmd = ReconcileCapabilityStateCommand()

        result = facade.reconcile(cmd)

        assert result.success is True
        assert result.message == "Reconciliation complete"
        assert "orphaned" in result.data
        assert "stale" in result.data
