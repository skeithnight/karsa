"""OutboxRepository contract — Sprint-07 Wave-2B."""
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from karsa.review.domain.aggregates.outbox_event import OutboxEvent


class OutboxRepository(ABC):
    """Repository contract for OutboxEvent aggregate.

    Transactional outbox for durable event publishing.
    Events saved within domain transaction, published by OutboxPublisherWorker.
    """

    @abstractmethod
    def save_event(self, event: OutboxEvent) -> None:
        """Saves a single outbox event.

        Args:
            event: The OutboxEvent to save.
        """
        pass

    @abstractmethod
    def save_events(self, events: List[OutboxEvent]) -> None:
        """Saves multiple outbox events atomically.

        All events are saved or none (transactional batch insert).

        Args:
            events: List of OutboxEvent instances to save.
        """
        pass

    @abstractmethod
    def get_pending(self, limit: int = 100) -> List[OutboxEvent]:
        """Retrieves pending outbox events for publishing.

        Uses FOR UPDATE SKIP LOCKED for concurrent publisher safety.

        Args:
            limit: Maximum number of events to retrieve.

        Returns:
            List of OutboxEvent instances with status PENDING, ordered by created_at.
        """
        pass

    @abstractmethod
    def get_failed(self, limit: int = 100) -> List[OutboxEvent]:
        """Retrieves failed outbox events for retry.

        Args:
            limit: Maximum number of events to retrieve.

        Returns:
            List of OutboxEvent instances with status FAILED, ordered by created_at.
        """
        pass

    @abstractmethod
    def mark_sent(self, outbox_id: str, sent_at: datetime) -> None:
        """Marks an outbox event as sent.

        Args:
            outbox_id: The outbox event identifier.
            sent_at: When the event was published.
        """
        pass

    @abstractmethod
    def mark_failed(self, outbox_id: str) -> None:
        """Marks an outbox event as failed.

        Args:
            outbox_id: The outbox event identifier.
        """
        pass

    @abstractmethod
    def increment_retry(self, outbox_id: str) -> None:
        """Increments the retry count for an outbox event.

        Args:
            outbox_id: The outbox event identifier.
        """
        pass

    @abstractmethod
    def cleanup_sent(self, before: datetime) -> int:
        """Deletes SENT outbox events older than the specified timestamp.

        Args:
            before: Delete SENT events with sent_at before this timestamp.

        Returns:
            Number of events deleted.
        """
        pass
