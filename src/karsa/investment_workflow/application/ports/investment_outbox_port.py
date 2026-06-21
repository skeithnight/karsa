"""InvestmentOutboxPort -- Sprint-13. ADR-140.

Port interface for investment workflow outbox.
Own dataclass to avoid cross-context dependency on capability_engine.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class InvestmentOutboxEvent:
    """Transactional outbox event for investment workflow."""

    outbox_id: str
    event_type: str
    payload: str  # JSON string
    aggregate_id: str
    status: str = "PENDING"  # PENDING, SENT, FAILED
    created_at: datetime = datetime.utcnow()
    sent_at: Optional[datetime] = None
    retry_count: int = 0


class InvestmentOutboxPort(ABC):
    """Transactional outbox port for investment workflow events."""

    @abstractmethod
    def save_event(self, event: InvestmentOutboxEvent) -> None:
        """Persist an event to the outbox."""

    @abstractmethod
    def get_pending(self, limit: int = 100) -> List[InvestmentOutboxEvent]:
        """Poll for unpublished events."""

    @abstractmethod
    def mark_sent(self, outbox_id: str) -> None:
        """Mark an event as delivered."""

    @abstractmethod
    def mark_failed(self, outbox_id: str) -> None:
        """Mark an event as failed."""

    @abstractmethod
    def get_failed(self, limit: int = 100) -> List[InvestmentOutboxEvent]:
        """Get failed events for dead-letter processing."""
