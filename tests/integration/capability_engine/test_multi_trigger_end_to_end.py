"""Integration: Multi-Trigger Evaluation -- Sprint-11. Wave-7.

Scenario 3: Same family_id + evaluation_id, three different trigger types.
Verify: ADR-120 identity -- three evolution records exist.
"""

import pytest

from karsa.capability_engine.application.capability_evolution_service import (
    EvolutionCommand,
)
from karsa.capability_engine.domain.value_objects.enums import (
    EvolutionTriggerType,
    EvolutionType,
)
from karsa.capability_engine.integration.capability_engine_bootstrap import bootstrap
from karsa.capability_engine.integration.capability_engine_fixture import (
    make_evolution,
    make_snapshot,
)


@pytest.fixture
def ctx():
    return bootstrap()


class TestMultiTriggerEvaluation:
    """ADR-120: One evolution per trigger type per evaluation cycle."""

    def test_three_triggers_same_eval(self, ctx):
        """Three different triggers for same (family, eval) -> three records."""
        snapshot = make_snapshot()

        triggers = [
            EvolutionTriggerType.REVIEW_FINDING,
            EvolutionTriggerType.ATTRIBUTION_INSIGHT,
            EvolutionTriggerType.EXECUTION_OUTCOME,
        ]

        for trigger in triggers:
            evo = make_evolution(trigger_type=trigger.value)
            cmd = EvolutionCommand(
                capability_family_id="int-family-001",
                evaluation_id="int-eval-001",
                trigger_type=trigger.value,
                capability_version_id="int-ver-001",
                capability_urn="urn:karsa:capability:ns:int-family-001:v1",
                evolution_type=EvolutionType.SCORE_ADJUSTMENT.value,
                delta=evo.delta,
                evidence=evo.evidence,
                context_snapshot=snapshot,
                evaluation_sequence=1,
                quality_score=0.8,
            )
            result = ctx.evolution_service.record_evolution(cmd)
            assert result.success is True

        # All three evolutions exist
        evolutions = ctx.evolution_repo.get_by_family_and_evaluation(
            "int-family-001", "int-eval-001"
        )
        assert len(evolutions) == 3

        trigger_types = {e.trigger_type for e in evolutions}
        assert trigger_types == {
            "REVIEW_FINDING",
            "ATTRIBUTION_INSIGHT",
            "EXECUTION_OUTCOME",
        }

    def test_each_trigger_has_canonical(self, ctx):
        """Each trigger type gets its own canonical entry."""
        snapshot = make_snapshot()

        for trigger in EvolutionTriggerType:
            evo = make_evolution(trigger_type=trigger.value)
            cmd = EvolutionCommand(
                capability_family_id="int-family-002",
                evaluation_id="int-eval-001",
                trigger_type=trigger.value,
                capability_version_id="int-ver-001",
                capability_urn="urn:karsa:capability:ns:int-family-002:v1",
                evolution_type=EvolutionType.SCORE_ADJUSTMENT.value,
                delta=evo.delta,
                evidence=evo.evidence,
                context_snapshot=snapshot,
                evaluation_sequence=1,
                quality_score=0.8,
            )
            ctx.evolution_service.record_evolution(cmd)

        # Each trigger has its own canonical
        for trigger in EvolutionTriggerType:
            canonical = ctx.version_registry.get_canonical(
                "int-family-002", "int-eval-001", trigger.value
            )
            assert canonical is not None
            assert canonical.evolution_status == "CANONICAL"

    def test_duplicate_trigger_rejected(self, ctx):
        """Same trigger for same (family, eval) -> duplicate rejected."""
        snapshot = make_snapshot()
        evo = make_evolution()

        cmd = EvolutionCommand(
            capability_family_id="int-family-003",
            evaluation_id="int-eval-001",
            trigger_type=EvolutionTriggerType.REVIEW_FINDING.value,
            capability_version_id="int-ver-001",
            capability_urn="urn:karsa:capability:ns:int-family-003:v1",
            evolution_type=EvolutionType.SCORE_ADJUSTMENT.value,
            delta=evo.delta,
            evidence=evo.evidence,
            context_snapshot=snapshot,
            evaluation_sequence=1,
            quality_score=0.8,
        )

        r1 = ctx.evolution_service.record_evolution(cmd)
        r2 = ctx.evolution_service.record_evolution(cmd)

        assert r1.success is True
        assert r2.success is False
