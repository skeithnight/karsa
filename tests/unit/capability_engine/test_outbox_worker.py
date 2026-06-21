"""Tests for CapabilityOutboxWorker -- Sprint-11. Wave-6.

Covers:
- pending retrieval
- retry logic
- batch processing
- skip locked semantics (simulated)
"""

import json
import pytest
from typing import Any, Dict

from karsa.capability_engine.application.capability_event_dispatcher import (
    CapabilityEventDispatcher,
)
from karsa.capability_engine.infrastructure.repositories.capability_evolution_outbox_repository import (
    OutboxEvent,
)
from karsa.capability_engine.infrastructure.persistence.in_memory_repositories import (
    InMemoryOutboxRepository,
)
from karsa.capability_engine.workers.capability_outbox_worker import (
    CapabilityOutboxWorker,
    OutboxWorkerResult,
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_RETRIES,
)


def _make_outbox_event(outbox_id="evt-001", status="PENDING", retry_count=0, **kwargs):
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


def _make_worker(batch_size=DEFAULT_BATCH_SIZE, max_retries=DEFAULT_MAX_RETRIES):
    outbox_repo = InMemoryOutboxRepository()
    dispatcher = CapabilityEventDispatcher()

    # Register a no-op handler for all supported events
    def noop_handler(payload):
        pass

    from karsa.capability_engine.application.capability_event_dispatcher import SUPPORTED_EVENT_TYPES
    for event_type in SUPPORTED_EVENT_TYPES:
        dispatcher.register(event_type, noop_handler)

    worker = CapabilityOutboxWorker(
        outbox_repo=outbox_repo,
        dispatcher=dispatcher,
        batch_size=batch_size,
        max_retries=max_retries,
    )
    return worker, outbox_repo, dispatcher


class TestPendingRetrieval:
    """Worker retrieves PENDING events from outbox."""

    def test_retrieves_pending_events(self):
        worker, outbox_repo, _ = _make_worker()
        outbox_repo.save_event(_make_outbox_event("evt-001"))
        outbox_repo.save_event(_make_outbox_event("evt-002"))

        result = worker.run()
        assert result.processed == 2
        assert result.sent == 2

    def test_ignores_sent_events(self):
        worker, outbox_repo, _ = _make_worker()
        outbox_repo.save_event(_make_outbox_event("evt-001", status="SENT"))
        outbox_repo.save_event(_make_outbox_event("evt-002"))

        result = worker.run()
        assert result.processed == 1
        assert result.sent == 1

    def test_ignores_failed_events(self):
        worker, outbox_repo, _ = _make_worker()
        outbox_repo.save_event(_make_outbox_event("evt-001", status="FAILED"))
        outbox_repo.save_event(_make_outbox_event("evt-002"))

        result = worker.run()
        assert result.processed == 1

    def test_empty_outbox(self):
        worker, _, _ = _make_worker()
        result = worker.run()
        assert result.processed == 0
        assert result.sent == 0
        assert result.failed == 0


class TestRetryLogic:
    """Failed events are retried with backoff."""

    def test_failed_event_marked_failed(self):
        worker, outbox_repo, dispatcher = _make_worker()

        # Register a failing handler
        def failing_handler(payload):
            raise RuntimeError("dispatch failed")

        dispatcher.register("CapabilityEvolutionRecordedEvent", failing_handler)

        outbox_repo.save_event(_make_outbox_event("evt-001"))
        result = worker.run()

        assert result.processed == 1
        assert result.failed == 1
        assert result.sent == 0

        # Verify event is now FAILED
        pending = outbox_repo.get_pending()
        assert len(pending) == 0  # no more PENDING

    def test_max_retries_skipped(self):
        worker, outbox_repo, _ = _make_worker(max_retries=3)
        outbox_repo.save_event(_make_outbox_event("evt-001", retry_count=3))

        result = worker.run()
        assert result.skipped == 1
        assert result.processed == 0

    def test_retry_count_increments_on_failure(self):
        worker, outbox_repo, dispatcher = _make_worker()

        def failing_handler(payload):
            raise RuntimeError("fail")

        dispatcher.register("CapabilityEvolutionRecordedEvent", failing_handler)

        event = _make_outbox_event("evt-001", retry_count=0)
        outbox_repo.save_event(event)

        worker.run()

        # The event should have retry_count incremented
        # After mark_failed, retry_count becomes 1
        stored = outbox_repo._store["evt-001"]
        assert stored.retry_count == 1
        assert stored.status == "FAILED"


class TestBatchProcessing:
    """Worker processes events in batches."""

    def test_respects_batch_size(self):
        worker, outbox_repo, _ = _make_worker(batch_size=2)

        for i in range(5):
            outbox_repo.save_event(_make_outbox_event(f"evt-{i:03d}"))

        result = worker.run()
        assert result.processed == 2
        assert result.sent == 2

    def test_batch_size_one(self):
        worker, outbox_repo, _ = _make_worker(batch_size=1)

        for i in range(3):
            outbox_repo.save_event(_make_outbox_event(f"evt-{i:03d}"))

        result = worker.run()
        assert result.processed == 1

    def test_invalid_json_marks_failed(self):
        worker, outbox_repo, _ = _make_worker()
        outbox_repo.save_event(OutboxEvent(
            outbox_id="evt-bad",
            event_type="CapabilityEvolutionRecordedEvent",
            payload="not-json",
            aggregate_id="f-001",
        ))

        result = worker.run()
        assert result.failed == 1
        assert result.sent == 0


class TestSkipLockedSemantics:
    """FOR UPDATE SKIP LOCKED simulation."""

    def test_concurrent_access_simulation(self):
        """Two workers should not process the same events."""
        outbox_repo = InMemoryOutboxRepository()
        dispatcher = CapabilityEventDispatcher()

        processed_by = []

        def tracking_handler(payload):
            processed_by.append(payload.get("outbox_id"))

        from karsa.capability_engine.application.capability_event_dispatcher import SUPPORTED_EVENT_TYPES
        for event_type in SUPPORTED_EVENT_TYPES:
            dispatcher.register(event_type, tracking_handler)

        # Add events
        for i in range(5):
            outbox_repo.save_event(_make_outbox_event(f"evt-{i:03d}"))

        # Worker 1 processes first batch
        worker1 = CapabilityOutboxWorker(
            outbox_repo=outbox_repo,
            dispatcher=dispatcher,
            batch_size=3,
        )
        result1 = worker1.run()

        # Worker 2 processes remaining
        worker2 = CapabilityOutboxWorker(
            outbox_repo=outbox_repo,
            dispatcher=dispatcher,
            batch_size=3,
        )
        result2 = worker2.run()

        assert result1.processed == 3
        assert result2.processed == 2
        assert result1.sent + result2.sent == 5
