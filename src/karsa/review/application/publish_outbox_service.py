"""PublishOutboxService — Sprint-07 Wave-3.

Publishes pending outbox events to the event journal.
Transaction boundary: Outbox read + journal write + status update.
"""
from datetime import datetime
from typing import Callable, Any

from karsa.review.domain.aggregates.outbox_event import OutboxEvent, OutboxStatus
from karsa.review.domain.repositories.outbox_repository import OutboxRepository
from karsa.review.application.dto import PublishOutboxCommand, PublishOutboxResponse


class PublishOutboxService:
    """Publishes pending outbox events to the event journal.

    Transaction boundary:
    1. Read pending events (FOR UPDATE SKIP LOCKED)
    2. Publish each event to journal
    3. Mark as SENT or FAILED
    """

    def __init__(
        self,
        outbox_repo: OutboxRepository,
        event_publisher: Callable[[Dict[str, Any]], None],
    ):
        self.outbox_repo = outbox_repo
        self.event_publisher = event_publisher

    def execute(self, command: PublishOutboxCommand) -> PublishOutboxResponse:
        """Executes the publish outbox command.

        All writes occur within a single transaction managed by the caller.

        Args:
            command: The publish outbox command.

        Returns:
            PublishOutboxResponse with publish details.
        """
        now = datetime.utcnow()
        published_count = 0
        failed_count = 0

        # 1. Get pending events
        pending_events = self.outbox_repo.get_pending(limit=command.batch_size)

        for event in pending_events:
            try:
                # 2. Publish to journal
                self.event_publisher(event.payload)

                # 3. Mark as sent
                self.outbox_repo.mark_sent(event.outbox_id, now)
                published_count += 1

            except Exception as e:
                # 4. Handle failure
                if event.retry_count >= command.max_retries:
                    self.outbox_repo.mark_failed(event.outbox_id)
                    failed_count += 1
                else:
                    self.outbox_repo.increment_retry(event.outbox_id)

        return PublishOutboxResponse(
            published_count=published_count,
            failed_count=failed_count,
            published_at=now.isoformat(),
        )
