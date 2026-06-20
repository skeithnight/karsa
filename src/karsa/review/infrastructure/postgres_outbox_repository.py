"""PostgresOutboxRepository — Sprint-07 Wave-2C."""
import json
from typing import List
from datetime import datetime

import psycopg

from karsa.review.domain.aggregates.outbox_event import OutboxEvent, OutboxStatus
from karsa.review.domain.repositories.outbox_repository import OutboxRepository
from karsa.review.infrastructure.jsonb_serializers import to_jsonb


class PostgresOutboxRepository(OutboxRepository):
    def __init__(self, conn):
        self.conn = conn

    def save_event(self, event: OutboxEvent) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO outbox_events (
                    outbox_id, event_type, payload, aggregate_id,
                    status, created_at, sent_at, retry_count
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event.outbox_id,
                    event.event_type,
                    to_jsonb(event.payload),
                    event.aggregate_id,
                    event.status,
                    event.created_at,
                    event.sent_at,
                    event.retry_count,
                )
            )

    def save_events(self, events: List[OutboxEvent]) -> None:
        if not events:
            return
        with self.conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO outbox_events (
                    outbox_id, event_type, payload, aggregate_id,
                    status, created_at, sent_at, retry_count
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        e.outbox_id, e.event_type, to_jsonb(e.payload),
                        e.aggregate_id, e.status, e.created_at,
                        e.sent_at, e.retry_count,
                    )
                    for e in events
                ]
            )

    def get_pending(self, limit: int = 100) -> List[OutboxEvent]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT outbox_id, event_type, payload, aggregate_id,
                       status, created_at, sent_at, retry_count
                FROM outbox_events
                WHERE status = 'PENDING'
                ORDER BY created_at
                LIMIT %s
                FOR UPDATE SKIP LOCKED
                """,
                (limit,)
            )
            rows = cur.fetchall()
            return [self._row_to_aggregate(r) for r in rows]

    def get_failed(self, limit: int = 100) -> List[OutboxEvent]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT outbox_id, event_type, payload, aggregate_id,
                       status, created_at, sent_at, retry_count
                FROM outbox_events
                WHERE status = 'FAILED'
                ORDER BY created_at
                LIMIT %s
                """,
                (limit,)
            )
            rows = cur.fetchall()
            return [self._row_to_aggregate(r) for r in rows]

    def mark_sent(self, outbox_id: str, sent_at: datetime) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE outbox_events SET status = 'SENT', sent_at = %s WHERE outbox_id = %s",
                (sent_at, outbox_id)
            )

    def mark_failed(self, outbox_id: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE outbox_events SET status = 'FAILED' WHERE outbox_id = %s",
                (outbox_id,)
            )

    def increment_retry(self, outbox_id: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE outbox_events SET retry_count = retry_count + 1 WHERE outbox_id = %s",
                (outbox_id,)
            )

    def cleanup_sent(self, before: datetime) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM outbox_events WHERE status = 'SENT' AND sent_at < %s",
                (before,)
            )
            return cur.rowcount

    def _row_to_aggregate(self, row) -> OutboxEvent:
        return OutboxEvent(
            outbox_id=row[0],
            event_type=row[1],
            payload=row[2] if isinstance(row[2], dict) else json.loads(row[2]) if row[2] else {},
            aggregate_id=row[3],
            status=row[4],
            created_at=row[5],
            sent_at=row[6],
            retry_count=row[7],
        )
