"""In-memory InvestmentOutboxPort -- Sprint-13."""

from datetime import datetime
from typing import Dict, List

from karsa.investment_workflow.application.ports.investment_outbox_port import (
    InvestmentOutboxEvent,
    InvestmentOutboxPort,
)


class InMemoryInvestmentOutboxRepository(InvestmentOutboxPort):
    """In-memory outbox repository for testing."""

    def __init__(self) -> None:
        self._store: Dict[str, InvestmentOutboxEvent] = {}

    def save_event(self, event: InvestmentOutboxEvent) -> None:
        self._store[event.outbox_id] = event

    def get_pending(self, limit: int = 100) -> List[InvestmentOutboxEvent]:
        pending = [e for e in self._store.values() if e.status == "PENDING"]
        return pending[:limit]

    def mark_sent(self, outbox_id: str) -> None:
        if outbox_id in self._store:
            old = self._store[outbox_id]
            self._store[outbox_id] = InvestmentOutboxEvent(
                outbox_id=old.outbox_id,
                event_type=old.event_type,
                payload=old.payload,
                aggregate_id=old.aggregate_id,
                status="SENT",
                created_at=old.created_at,
                sent_at=datetime.utcnow(),
                retry_count=old.retry_count,
            )

    def mark_failed(self, outbox_id: str) -> None:
        if outbox_id in self._store:
            old = self._store[outbox_id]
            self._store[outbox_id] = InvestmentOutboxEvent(
                outbox_id=old.outbox_id,
                event_type=old.event_type,
                payload=old.payload,
                aggregate_id=old.aggregate_id,
                status="FAILED",
                created_at=old.created_at,
                retry_count=old.retry_count + 1,
            )

    def get_failed(self, limit: int = 100) -> List[InvestmentOutboxEvent]:
        failed = [e for e in self._store.values() if e.status == "FAILED"]
        return failed[:limit]
