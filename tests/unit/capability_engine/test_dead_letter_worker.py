"""Tests for CapabilityDeadLetterWorker -- Sprint-11. Wave-6.

Covers:
- retry success
- retry exhaustion
- dead letter transition
"""

import json
import pytest
from typing import Any, Dict

from karsa.capability_engine.application.capability_event_dispatcher import (
    CapabilityEventDispatcher,
    SUPPORTED_EVENT_TYPES,
)
from karsa.capability_engine.infrastructure.repositories.capability_evolution_outbox_repository import (
    OutboxEvent,
)
from karsa.capability_engine.infrastructure.persistence.in_memory_repositories import (
    InMemoryOutboxRepository,
)
from karsa.capability_engine.workers.capability_dead_letter_worker import (
    CapabilityDeadLetterWorker,
    DeadLetterWorkerResult,
    DEFAULT_DEAD_LETTER_THRESHOLD,
)


def _make_outbox_event(outbox_id="evt-001", status="FAILED", retry_count=0, **kwargs):
    defaults = dict(
        outbox_id=outbox_id,
        event_type="CapabilityEvolutionRecordedEvent",
        payload=json.dumps({"evolution_id": "evo-001", "capability_family_id": "f-001"}),
        aggregate_id="f-001",
        status=status,
        retry_count=retry_count,
    )
    defaults.update(kwargs)
    return OutboxEvent(**defaults)


def _make_worker(threshold=DEFAULT_DEAD_LETTER_THRESHOLD):
    outbox_repo = InMemoryOutboxRepository()
    dispatcher = CapabilityEventDispatcher()

    def noop_handler(payload):
        pass

    for event_type in SUPPORTED_EVENT_TYPES:
        dispatcher.register(event_type, noop_handler)

    worker = CapabilityDeadLetterWorker(
        outbox_repo=outbox_repo,
        dispatcher=dispatcher,
        dead_letter_threshold=threshold,
    )
    return worker, outbox_repo, dispatcher


class TestRetrySuccess:
    """Failed events can be retried successfully."""

    def test_retry_sends_event(self):
        worker, outbox_repo, _ = _make_worker()
        outbox_repo.save_event(_make_outbox_event("evt-001", retry_count=1))

        result = worker.run()
        assert result.retried == 1
        assert result.sent == 1

    def test_retry_multiple_events(self):
        worker, outbox_repo, _ = _make_worker()
        for i in range(3):
            outbox_repo.save_event(_make_outbox_event(f"evt-{i:03d}", retry_count=1))

        result = worker.run()
        assert result.retried == 3
        assert result.sent == 3

    def test_no_failed_events(self):
        worker, outbox_repo, _ = _make_worker()
        outbox_repo.save_event(_make_outbox_event("evt-001", status="PENDING"))

        result = worker.run()
        assert result.retried == 0
        assert result.sent == 0

    def test_ignores_sent_events(self):
        worker, outbox_repo, _ = _make_worker()
        outbox_repo.save_event(_make_outbox_event("evt-001", status="SENT"))

        result = worker.run()
        assert result.retried == 0


class TestRetryExhaustion:
    """Events at max retries are not retried."""

    def test_exhausted_event_not_retried(self):
        worker, outbox_repo, _ = _make_worker(threshold=3)
        outbox_repo.save_event(_make_outbox_event("evt-001", retry_count=3))

        result = worker.run()
        assert result.retried == 0
        assert result.dead_lettered == 1

    def test_below_threshold_still_retried(self):
        worker, outbox_repo, _ = _make_worker(threshold=5)
        outbox_repo.save_event(_make_outbox_event("evt-001", retry_count=4))

        result = worker.run()
        assert result.retried == 1
        assert result.dead_lettered == 0


class TestDeadLetterTransition:
    """Events transition to dead letter after exhaustion."""

    def test_dead_letter_count(self):
        worker, outbox_repo, _ = _make_worker(threshold=2)

        # Events at different retry counts
        outbox_repo.save_event(_make_outbox_event("evt-ok", retry_count=1))
        outbox_repo.save_event(_make_outbox_event("evt-exhausted", retry_count=2))
        outbox_repo.save_event(_make_outbox_event("evt-over", retry_count=5))

        result = worker.run()
        assert result.retried == 1
        assert result.dead_lettered == 2

    def test_dead_letter_threshold_configurable(self):
        worker, _, _ = _make_worker(threshold=10)
        assert worker.dead_letter_threshold == 10

    def test_failing_handler_increments_retry(self):
        worker, outbox_repo, dispatcher = _make_worker(threshold=5)

        def failing_handler(payload):
            raise RuntimeError("still broken")

        dispatcher.register("CapabilityEvolutionRecordedEvent", failing_handler)
        outbox_repo.save_event(_make_outbox_event("evt-001", retry_count=1))

        result = worker.run()
        # Event was retried but handler failed again
        assert result.retried == 1
        # Retry count should be incremented
        stored = outbox_repo._store["evt-001"]
        assert stored.retry_count == 2
