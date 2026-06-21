"""Integration: Outbox Processing -- Sprint-11. Wave-7.

End-to-end: PENDING -> dispatch -> SENT/FAILED.
"""

import json
import pytest

from karsa.capability_engine.infrastructure.repositories.capability_evolution_outbox_repository import (
    OutboxEvent,
)
from karsa.capability_engine.integration.capability_engine_bootstrap import bootstrap


@pytest.fixture
def ctx():
    return bootstrap()


class TestOutboxEndToEnd:
    """Outbox PENDING -> SENT and PENDING -> FAILED flows."""

    def test_pending_event_dispatched_to_sent(self, ctx):
        # Register a handler
        handled = []

        def handler(payload):
            handled.append(payload)

        ctx.dispatcher.register("CapabilityEvolutionRecordedEvent", handler)

        # Save event to outbox
        event = OutboxEvent(
            outbox_id="int-evt-001",
            event_type="CapabilityEvolutionRecordedEvent",
            payload=json.dumps({"evolution_id": "evo-001"}),
            aggregate_id="int-family-001",
        )
        ctx.outbox_repo.save_event(event)

        # Process via outbox worker
        result = ctx.outbox_worker.run()

        assert result.processed == 1
        assert result.sent == 1
        assert result.failed == 0
        assert len(handled) == 1

    def test_failed_dispatch_marks_failed(self, ctx):
        # Register a failing handler
        def failing_handler(payload):
            raise RuntimeError("dispatch error")

        ctx.dispatcher.register("CapabilityEvolutionRecordedEvent", failing_handler)

        event = OutboxEvent(
            outbox_id="int-evt-002",
            event_type="CapabilityEvolutionRecordedEvent",
            payload=json.dumps({"evolution_id": "evo-002"}),
            aggregate_id="int-family-001",
        )
        ctx.outbox_repo.save_event(event)

        result = ctx.outbox_worker.run()

        assert result.processed == 1
        assert result.failed == 1
        assert result.sent == 0

    def test_batch_processing(self, ctx):
        ctx.dispatcher.register(
            "CapabilityEvolutionRecordedEvent", lambda p: None
        )

        for i in range(5):
            ctx.outbox_repo.save_event(OutboxEvent(
                outbox_id=f"int-evt-{i:03d}",
                event_type="CapabilityEvolutionRecordedEvent",
                payload=json.dumps({"evolution_id": f"evo-{i:03d}"}),
                aggregate_id="int-family-001",
            ))

        result = ctx.outbox_worker.run()
        assert result.processed == 5
        assert result.sent == 5

    def test_evolution_service_creates_outbox_event(self, ctx):
        """Full flow: EvolutionService -> Outbox -> Worker -> Dispatch."""
        from karsa.capability_engine.application.capability_evolution_service import (
            EvolutionCommand,
        )
        from karsa.capability_engine.domain.value_objects.enums import (
            EvolutionTriggerType,
            EvolutionType,
        )
        from karsa.capability_engine.integration.capability_engine_fixture import (
            make_evolution,
            make_snapshot,
        )

        handled = []
        ctx.dispatcher.register(
            "CapabilityEvolutionRecordedEvent",
            lambda p: handled.append(p),
        )

        evo = make_evolution()
        cmd = EvolutionCommand(
            capability_family_id=evo.capability_family_id,
            evaluation_id=evo.evaluation_id,
            trigger_type=EvolutionTriggerType.REVIEW_FINDING.value,
            capability_version_id=evo.capability_version_id,
            capability_urn=evo.capability_urn,
            evolution_type=EvolutionType.SCORE_ADJUSTMENT.value,
            delta=evo.delta,
            evidence=evo.evidence,
            context_snapshot=evo.context_snapshot,
            evaluation_sequence=1,
            quality_score=0.8,
        )
        ctx.evolution_service.record_evolution(cmd)

        # Outbox has the event
        pending = ctx.outbox_repo.get_pending()
        assert len(pending) == 1

        # Worker dispatches it
        result = ctx.outbox_worker.run()
        assert result.sent == 1
        assert len(handled) == 1
