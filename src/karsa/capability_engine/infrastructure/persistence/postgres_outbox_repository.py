"""PostgresCapabilityEvolutionOutboxRepository -- Sprint-11."""

from datetime import datetime
from typing import List

import psycopg

from karsa.capability_engine.infrastructure.repositories.capability_evolution_outbox_repository import (
    CapabilityEvolutionOutboxRepository,
    OutboxEvent,
)

TABLE = "capability_evolution_outbox"


class PostgresCapabilityEvolutionOutboxRepository(
    CapabilityEvolutionOutboxRepository
):
    """Transactional outbox for durable event publishing."""

    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def save_event(self, event: OutboxEvent) -> None:
        sql = f"""
            INSERT INTO {TABLE} (
                outbox_id, event_type, payload, aggregate_id,
                status, created_at, sent_at, retry_count
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        with self.conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    event.outbox_id,
                    event.event_type,
                    event.payload,
                    event.aggregate_id,
                    event.status,
                    event.created_at,
                    event.sent_at,
                    event.retry_count,
                ),
            )

    def get_pending(self, limit: int = 100) -> List[OutboxEvent]:
        sql = f"""
            SELECT * FROM {TABLE}
            WHERE status = 'PENDING'
            ORDER BY created_at ASC
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (limit,))
            return [self._row_to_event(row) for row in cur.fetchall()]

    def mark_sent(self, outbox_id: str) -> None:
        sql = f"""
            UPDATE {TABLE}
            SET status = 'SENT', sent_at = NOW()
            WHERE outbox_id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (outbox_id,))

    def mark_failed(self, outbox_id: str) -> None:
        sql = f"""
            UPDATE {TABLE}
            SET status = 'FAILED', retry_count = retry_count + 1
            WHERE outbox_id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (outbox_id,))

    def increment_retry(self, outbox_id: str) -> None:
        sql = f"""
            UPDATE {TABLE}
            SET retry_count = retry_count + 1
            WHERE outbox_id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (outbox_id,))

    def get_failed(self, limit: int = 100) -> List[OutboxEvent]:
        sql = f"""
            SELECT * FROM {TABLE}
            WHERE status = 'FAILED'
            ORDER BY created_at ASC
            LIMIT %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (limit,))
            return [self._row_to_event(row) for row in cur.fetchall()]

    def _row_to_event(self, row: tuple) -> OutboxEvent:
        return OutboxEvent(
            outbox_id=row[0],
            event_type=row[1],
            payload=row[2],
            aggregate_id=row[3],
            status=row[4],
            created_at=row[5],
            sent_at=row[6],
            retry_count=row[7],
        )
