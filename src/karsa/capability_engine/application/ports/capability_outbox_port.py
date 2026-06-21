"""CapabilityOutboxPort -- Sprint-11. Wave-9R. TD-004.

Port interface for transactional outbox.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class OutboxEvent:
    """Transactional outbox event entry."""

    outbox_id: str
    event_type: str
    payload: str  # JSON string
    aggregate_id: str
    status: str = "PENDING"  # PENDING, SENT, FAILED
    created_at: datetime = datetime.utcnow()
    sent_at: Optional[datetime] = None
    retry_count: int = 0


class CapabilityOutboxPort(ABC):
    """Transactional outbox port for durable event publishing."""

    @abstractmethod
    def save_event(self, event: OutboxEvent) -> None:
        """Persist an event to the outbox."""

    @abstractmethod
    def get_pending(self, limit: int = 100) -> List[OutboxEvent]:
        """Poll for unpublished events with FOR UPDATE SKIP LOCKED."""

    @abstractmethod
    def mark_sent(self, outbox_id: str) -> None:
        """Mark an event as delivered."""

    @abstractmethod
    def mark_failed(self, outbox_id: str) -> None:
        """Mark an event as failed for retry."""

    @abstractmethod
    def increment_retry(self, outbox_id: str) -> None:
        """Increment retry count."""

    @abstractmethod
    def get_failed(self, limit: int = 100) -> List[OutboxEvent]:
        """Get failed events for dead-letter processing."""
