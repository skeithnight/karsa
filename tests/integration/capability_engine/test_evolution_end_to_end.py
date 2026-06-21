"""Integration: Evolution Creation Flow -- Sprint-11. Wave-7.

Scenario 1: Review Finding input.
Verify: Evolution saved, Registry canonical created, Outbox event created.
ADR-120, ADR-133.
"""

import pytest

from karsa.capability_engine.application.capability_evolution_service import (
    EvolutionCommand,
)
from karsa.capability_engine.domain.value_objects.enums import (
    EvolutionTriggerType,
    EvolutionType,
    EvolutionStatus,
)
from karsa.capability_engine.integration.capability_engine_bootstrap import bootstrap
from karsa.capability_engine.integration.capability_engine_fixture import (
    make_evolution,
    make_snapshot,
)


@pytest.fixture
def ctx():
    return bootstrap()


class TestEvolutionCreationFlow:
    """End-to-end: Review Finding -> Evolution -> Registry -> Outbox."""

    def test_evolution_saved_to_repository(self, ctx):
        evo = make_evolution()
        saved = ctx.evolution_repo.save(evo)
        assert saved is True

        loaded = ctx.evolution_repo.get_by_id(evo.evolution_id)
        assert loaded is not None
        assert loaded.capability_family_id == evo.capability_family_id

    def test_evolution_via_service(self, ctx):
        snapshot = make_snapshot()
        cmd = EvolutionCommand(
            capability_family_id="int-family-001",
            evaluation_id="int-eval-001",
            trigger_type=EvolutionTriggerType.REVIEW_FINDING.value,
            capability_version_id="int-ver-001",
            capability_urn="urn:karsa:capability:ns:int-family-001:v1",
            evolution_type=EvolutionType.SCORE_ADJUSTMENT.value,
            delta=make_evolution().delta,
            evidence=make_evolution().evidence,
            context_snapshot=snapshot,
            evaluation_sequence=1,
            quality_score=0.8,
        )
        result = ctx.evolution_service.record_evolution(cmd)

        assert result.success is True
        assert result.evolution_id is not None
        assert result.deferred is False

    def test_registry_canonical_created(self, ctx):
        snapshot = make_snapshot()
        cmd = EvolutionCommand(
            capability_family_id="int-family-001",
            evaluation_id="int-eval-001",
            trigger_type=EvolutionTriggerType.REVIEW_FINDING.value,
            capability_version_id="int-ver-001",
            capability_urn="urn:karsa:capability:ns:int-family-001:v1",
            evolution_type=EvolutionType.SCORE_ADJUSTMENT.value,
            delta=make_evolution().delta,
            evidence=make_evolution().evidence,
            context_snapshot=snapshot,
            evaluation_sequence=1,
            quality_score=0.8,
        )
        result = ctx.evolution_service.record_evolution(cmd)

        canonical = ctx.version_registry.get_canonical(
            "int-family-001", "int-eval-001", "REVIEW_FINDING"
        )
        assert canonical is not None
        assert canonical.evolution_id == result.evolution_id
        assert canonical.evolution_status == EvolutionStatus.CANONICAL.value

    def test_outbox_event_created(self, ctx):
        snapshot = make_snapshot()
        cmd = EvolutionCommand(
            capability_family_id="int-family-001",
            evaluation_id="int-eval-001",
            trigger_type=EvolutionTriggerType.REVIEW_FINDING.value,
            capability_version_id="int-ver-001",
            capability_urn="urn:karsa:capability:ns:int-family-001:v1",
            evolution_type=EvolutionType.SCORE_ADJUSTMENT.value,
            delta=make_evolution().delta,
            evidence=make_evolution().evidence,
            context_snapshot=snapshot,
            evaluation_sequence=1,
            quality_score=0.8,
        )
        ctx.evolution_service.record_evolution(cmd)

        pending = ctx.outbox_repo.get_pending()
        assert len(pending) == 1
        assert pending[0].event_type == "CapabilityEvolutionRecordedEvent"

    def test_duplicate_evolution_rejected(self, ctx):
        """ADR-120: Same business key -> ON CONFLICT DO NOTHING."""
        snapshot = make_snapshot()
        cmd = EvolutionCommand(
            capability_family_id="int-family-001",
            evaluation_id="int-eval-001",
            trigger_type=EvolutionTriggerType.REVIEW_FINDING.value,
            capability_version_id="int-ver-001",
            capability_urn="urn:karsa:capability:ns:int-family-001:v1",
            evolution_type=EvolutionType.SCORE_ADJUSTMENT.value,
            delta=make_evolution().delta,
            evidence=make_evolution().evidence,
            context_snapshot=snapshot,
            evaluation_sequence=1,
            quality_score=0.8,
        )
        r1 = ctx.evolution_service.record_evolution(cmd)
        r2 = ctx.evolution_service.record_evolution(cmd)

        assert r1.success is True
        assert r2.success is False
