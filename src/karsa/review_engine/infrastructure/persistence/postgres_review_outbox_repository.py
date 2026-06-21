"""PostgresReviewOutboxRepository — Sprint-10.

Transactional outbox for durable event publishing.
"""
import json
from typing import List
from datetime import datetime
import psycopg

from karsa.review_engine.infrastructure.repositories.review_outbox_repository import (
    ReviewOutboxRepository, OutboxEvent,
)


class PostgresReviewOutboxRepository(ReviewOutboxRepository):
    def __init__(self, conn):
        self.conn = conn

    def save_event(self, event: OutboxEvent) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_outbox (
                    outbox_id, event_type, payload, aggregate_id,
                    status, created_at, sent_at, retry_count
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event.outbox_id,
                    event.event_type,
                    event.payload,
                    event.aggregate_id,
                    event.status,
                    event.created_at,
                    event.sent_at,
                    event.retry_count,
                )
            )

    def get_pending(self, limit: int = 100) -> List[OutboxEvent]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT outbox_id, event_type, payload, aggregate_id,
                       status, created_at, sent_at, retry_count
                FROM review_outbox
                WHERE status = 'PENDING'
                ORDER BY created_at
                LIMIT %s
                FOR UPDATE SKIP LOCKED
                """,
                (limit,)
            )
            return [self._row_to_event(r) for r in cur.fetchall()]

    def mark_sent(self, outbox_id: str, sent_at: datetime) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE review_outbox SET status = 'SENT', sent_at = %s WHERE outbox_id = %s",
                (sent_at, outbox_id)
            )

    def mark_failed(self, outbox_id: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE review_outbox SET status = 'FAILED' WHERE outbox_id = %s",
                (outbox_id,)
            )

    def _row_to_event(self, row) -> OutboxEvent:
        return OutboxEvent(
            outbox_id=row[0],
            event_type=row[1],
            payload=row[2] if isinstance(row[2], str) else json.dumps(row[2]),
            aggregate_id=row[3],
            status=row[4],
            created_at=row[5],
            sent_at=row[6],
            retry_count=row[7],
        )
