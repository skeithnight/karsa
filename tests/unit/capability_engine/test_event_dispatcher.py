"""Tests for CapabilityEventDispatcher -- Sprint-11. Wave-6.

Covers:
- event routing
- unknown event rejection
- ordering guarantees
"""

import pytest
from typing import Any, Dict, List

from karsa.capability_engine.application.capability_event_dispatcher import (
    CapabilityEventDispatcher,
    DispatchResult,
    SUPPORTED_EVENT_TYPES,
)


class TestEventRouting:
    """Events are routed to their registered handlers."""

    def test_dispatch_to_registered_handler(self):
        dispatcher = CapabilityEventDispatcher()
        calls = []

        def handler(payload: Dict[str, Any]) -> None:
            calls.append(payload)

        dispatcher.register("CapabilityEvolutionRecordedEvent", handler)
        result = dispatcher.dispatch(
            "CapabilityEvolutionRecordedEvent", {"evolution_id": "evo-001"}
        )

        assert result.handled is True
        assert result.handler_name == "handler"
        assert len(calls) == 1
        assert calls[0]["evolution_id"] == "evo-001"

    def test_dispatch_multiple_event_types(self):
        dispatcher = CapabilityEventDispatcher()
        calls = []

        def handler_a(payload):
            calls.append(("A", payload))

        def handler_b(payload):
            calls.append(("B", payload))

        dispatcher.register("CapabilityEvolutionRecordedEvent", handler_a)
        dispatcher.register("CapabilityHealthScoreUpdatedEvent", handler_b)

        dispatcher.dispatch("CapabilityEvolutionRecordedEvent", {"id": 1})
        dispatcher.dispatch("CapabilityHealthScoreUpdatedEvent", {"id": 2})

        assert len(calls) == 2
        assert calls[0] == ("A", {"id": 1})
        assert calls[1] == ("B", {"id": 2})

    def test_dispatch_returns_handler_name(self):
        dispatcher = CapabilityEventDispatcher()

        def my_handler(payload):
            pass

        dispatcher.register(
            "CapabilityEvolutionRecordedEvent", my_handler, "custom_name"
        )
        result = dispatcher.dispatch(
            "CapabilityEvolutionRecordedEvent", {}
        )
        assert result.handler_name == "custom_name"

    def test_dispatch_no_handler_registered(self):
        dispatcher = CapabilityEventDispatcher()
        result = dispatcher.dispatch(
            "CapabilityEvolutionRecordedEvent", {}
        )
        assert result.handled is False
        assert "No handler" in result.error

    def test_dispatch_handler_exception(self):
        dispatcher = CapabilityEventDispatcher()

        def failing_handler(payload):
            raise RuntimeError("handler failed")

        dispatcher.register("CapabilityEvolutionRecordedEvent", failing_handler)
        result = dispatcher.dispatch(
            "CapabilityEvolutionRecordedEvent", {}
        )
        assert result.handled is False
        assert "handler failed" in result.error

    def test_has_handler(self):
        dispatcher = CapabilityEventDispatcher()
        assert dispatcher.has_handler("CapabilityEvolutionRecordedEvent") is False

        dispatcher.register("CapabilityEvolutionRecordedEvent", lambda p: None)
        assert dispatcher.has_handler("CapabilityEvolutionRecordedEvent") is True

    def test_registered_event_types(self):
        dispatcher = CapabilityEventDispatcher()
        dispatcher.register("CapabilityEvolutionRecordedEvent", lambda p: None)
        dispatcher.register("CapabilityHealthScoreUpdatedEvent", lambda p: None)

        types = dispatcher.registered_event_types
        assert len(types) == 2
        assert "CapabilityEvolutionRecordedEvent" in types


class TestUnknownEventRejection:
    """Unknown event types are rejected, not silently dropped."""

    def test_unknown_event_type_raises(self):
        dispatcher = CapabilityEventDispatcher()
        with pytest.raises(ValueError, match="Unknown event type"):
            dispatcher.dispatch("UnknownEventType", {})

    def test_all_supported_types_are_known(self):
        """All event types in SUPPORTED_EVENT_TYPES should be accepted."""
        dispatcher = CapabilityEventDispatcher()
        for event_type in SUPPORTED_EVENT_TYPES:
            # Should not raise
            result = dispatcher.dispatch(event_type, {})
            # Will return handled=False since no handler registered, but no ValueError
            assert result.event_type == event_type

    def test_supported_event_types_frozenset(self):
        assert isinstance(SUPPORTED_EVENT_TYPES, frozenset)
        assert len(SUPPORTED_EVENT_TYPES) == 8


class TestOrderingGuarantees:
    """Events are dispatched in order."""

    def test_dispatch_preserves_order(self):
        dispatcher = CapabilityEventDispatcher()
        order = []

        def tracking_handler(payload):
            order.append(payload["seq"])

        dispatcher.register("CapabilityEvolutionRecordedEvent", tracking_handler)

        for i in range(10):
            dispatcher.dispatch(
                "CapabilityEvolutionRecordedEvent", {"seq": i}
            )

        assert order == list(range(10))

    def test_dispatch_batch_preserves_order(self):
        dispatcher = CapabilityEventDispatcher()
        order = []

        def tracking_handler(payload):
            order.append(payload["seq"])

        dispatcher.register("CapabilityEvolutionRecordedEvent", tracking_handler)

        events = [
            ("CapabilityEvolutionRecordedEvent", {"seq": i})
            for i in range(5)
        ]
        results = dispatcher.dispatch_batch(events)

        assert order == list(range(5))
        assert len(results) == 5
        assert all(r.handled for r in results)

    def test_dispatch_batch_continues_on_failure(self):
        dispatcher = CapabilityEventDispatcher()
        call_count = {"n": 0}

        def counting_handler(payload):
            call_count["n"] += 1

        def failing_handler(payload):
            raise RuntimeError("fail")

        dispatcher.register("CapabilityEvolutionRecordedEvent", counting_handler)
        dispatcher.register("CapabilityHealthScoreUpdatedEvent", failing_handler)

        events = [
            ("CapabilityEvolutionRecordedEvent", {"id": 1}),
            ("CapabilityHealthScoreUpdatedEvent", {"id": 2}),
            ("CapabilityEvolutionRecordedEvent", {"id": 3}),
        ]
        results = dispatcher.dispatch_batch(events)

        assert call_count["n"] == 2  # two evolution events processed
        assert results[0].handled is True
        assert results[1].handled is False
        assert results[2].handled is True
