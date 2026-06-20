"""OutboxEvent aggregate — Sprint-07 Wave-1."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from karsa.review.domain.value_objects.review_verdict import ReviewType


class OutboxStatus:
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


@dataclass
class OutboxEvent:
    """Transactional outbox event for durable publishing.

    Created within the same transaction as domain aggregates.
    PublisherWorker reads PENDING records and publishes to event journal.
    """
    outbox_id: str
    event_type: str
    payload: dict
    aggregate_id: str
    status: str = OutboxStatus.PENDING
    created_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    retry_count: int = 0

    def __post_init__(self):
        if not self.outbox_id or not self.outbox_id.strip():
            raise ValueError("outbox_id cannot be empty.")
        if not self.event_type or not self.event_type.strip():
            raise ValueError("event_type cannot be empty.")
        if not self.aggregate_id or not self.aggregate_id.strip():
            raise ValueError("aggregate_id cannot be empty.")
        if self.status not in (OutboxStatus.PENDING, OutboxStatus.SENT, OutboxStatus.FAILED):
            raise ValueError(f"Invalid status: {self.status}")

    def mark_sent(self, sent_at: datetime) -> None:
        """Marks event as sent. Raises if already sent."""
        if self.status == OutboxStatus.SENT:
            raise ValueError("Event already sent.")
        object.__setattr__(self, 'status', OutboxStatus.SENT)
        object.__setattr__(self, 'sent_at', sent_at)

    def mark_failed(self) -> None:
        """Marks event as failed."""
        object.__setattr__(self, 'status', OutboxStatus.FAILED)

    def increment_retry(self) -> None:
        """Increments retry count."""
        object.__setattr__(self, 'retry_count', self.retry_count + 1)

    @property
    def is_pending(self) -> bool:
        return self.status == OutboxStatus.PENDING

    @property
    def is_sent(self) -> bool:
        return self.status == OutboxStatus.SENT

    @property
    def is_failed(self) -> bool:
        return self.status == OutboxStatus.FAILED
