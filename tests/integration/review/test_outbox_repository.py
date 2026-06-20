"""Outbox repository tests — Sprint-07 Wave-2C."""
import pytest
from datetime import datetime
from typing import List, Dict

from karsa.review.domain.aggregates.outbox_event import OutboxEvent, OutboxStatus
from karsa.review.domain.repositories.outbox_repository import OutboxRepository


class InMemoryOutboxRepository(OutboxRepository):
    def __init__(self):
        self._store: Dict[str, OutboxEvent] = {}

    def save_event(self, event: OutboxEvent) -> None:
        self._store[event.outbox_id] = event

    def save_events(self, events: List[OutboxEvent]) -> None:
        for e in events:
            self.save_event(e)

    def get_pending(self, limit: int = 100) -> List[OutboxEvent]:
        pending = [e for e in self._store.values() if e.is_pending]
        pending.sort(key=lambda e: e.created_at or datetime.min)
        return pending[:limit]

    def get_failed(self, limit: int = 100) -> List[OutboxEvent]:
        failed = [e for e in self._store.values() if e.is_failed]
        failed.sort(key=lambda e: e.created_at or datetime.min)
        return failed[:limit]

    def mark_sent(self, outbox_id: str, sent_at: datetime) -> None:
        if outbox_id in self._store:
            self._store[outbox_id].mark_sent(sent_at)

    def mark_failed(self, outbox_id: str) -> None:
        if outbox_id in self._store:
            self._store[outbox_id].mark_failed()

    def increment_retry(self, outbox_id: str) -> None:
        if outbox_id in self._store:
            self._store[outbox_id].increment_retry()

    def cleanup_sent(self, before: datetime) -> int:
        to_delete = [
            oid for oid, e in self._store.items()
            if e.is_sent and e.sent_at and e.sent_at < before
        ]
        for oid in to_delete:
            del self._store[oid]
        return len(to_delete)


def _make_event(outbox_id="out-1", event_type="TestEvent", aggregate_id="a1"):
    return OutboxEvent(
        outbox_id=outbox_id,
        event_type=event_type,
        payload={"key": "value"},
        aggregate_id=aggregate_id,
        created_at=datetime.utcnow(),
    )


class TestOutboxRepository:
    def test_save_and_get_pending(self):
        repo = InMemoryOutboxRepository()
        event = _make_event()
        repo.save_event(event)
        pending = repo.get_pending()
        assert len(pending) == 1
        assert pending[0].outbox_id == "out-1"

    def test_batch_save(self):
        repo = InMemoryOutboxRepository()
        events = [_make_event(f"out-{i}", aggregate_id=f"a{i}") for i in range(5)]
        repo.save_events(events)
        assert len(repo.get_pending()) == 5

    def test_mark_sent(self):
        repo = InMemoryOutboxRepository()
        event = _make_event()
        repo.save_event(event)
        now = datetime.utcnow()
        repo.mark_sent("out-1", now)
        assert repo.get_pending() == []
        assert event.is_sent
        assert event.sent_at == now

    def test_mark_failed(self):
        repo = InMemoryOutboxRepository()
        event = _make_event()
        repo.save_event(event)
        repo.mark_failed("out-1")
        assert repo.get_pending() == []
        assert event.is_failed

    def test_get_failed(self):
        repo = InMemoryOutboxRepository()
        event = _make_event()
        repo.save_event(event)
        repo.mark_failed("out-1")
        failed = repo.get_failed()
        assert len(failed) == 1

    def test_increment_retry(self):
        repo = InMemoryOutboxRepository()
        event = _make_event()
        repo.save_event(event)
        assert event.retry_count == 0
        repo.increment_retry("out-1")
        assert event.retry_count == 1
        repo.increment_retry("out-1")
        assert event.retry_count == 2

    def test_cleanup_sent(self):
        repo = InMemoryOutboxRepository()
        event = _make_event()
        repo.save_event(event)
        repo.mark_sent("out-1", datetime(2026, 1, 1))
        deleted = repo.cleanup_sent(datetime(2026, 6, 1))
        assert deleted == 1
        assert repo.get_pending() == []

    def test_cleanup_preserves_recent(self):
        repo = InMemoryOutboxRepository()
        event = _make_event()
        repo.save_event(event)
        repo.mark_sent("out-1", datetime.utcnow())
        deleted = repo.cleanup_sent(datetime(2020, 1, 1))
        assert deleted == 0

    def test_pending_order(self):
        repo = InMemoryOutboxRepository()
        for i in range(5):
            repo.save_event(_make_event(f"out-{i}", aggregate_id=f"a{i}"))
        pending = repo.get_pending(limit=3)
        assert len(pending) == 3

    def test_empty_pending(self):
        repo = InMemoryOutboxRepository()
        assert repo.get_pending() == []
