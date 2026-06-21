"""AttributionOutboxRepository — Sprint-09.

Transactional outbox for durable event publishing.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class OutboxEvent:
    outbox_id: str
    event_type: str
    payload: str  # JSON
    aggregate_id: str
    status: str  # PENDING | SENT | FAILED
    created_at: datetime
    sent_at: Optional[datetime] = None
    retry_count: int = 0


class AttributionOutboxRepository(ABC):

    @abstractmethod
    def save_event(self, event: OutboxEvent) -> None:
        ...

    @abstractmethod
    def get_pending(self, limit: int = 100) -> List[OutboxEvent]:
        ...

    @abstractmethod
    def mark_sent(self, outbox_id: str) -> None:
        ...

    @abstractmethod
    def mark_failed(self, outbox_id: str) -> None:
        ...

    @abstractmethod
    def increment_retry(self, outbox_id: str) -> None:
        ...
