"""PostgresReviewCycleStatusProjectionRepository — Sprint-07 Wave-2C."""
from typing import Optional, List
from datetime import datetime

from karsa.review.domain.repositories.review_cycle_status_projection_repository import (
    ReviewCycleStatusProjectionRepository, ReviewCycleStatusProjection,
)


class PostgresReviewCycleStatusProjectionRepository(ReviewCycleStatusProjectionRepository):
    def __init__(self, conn):
        self.conn = conn

    def get_by_cycle_id(self, cycle_id: str) -> Optional[ReviewCycleStatusProjection]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT cycle_id, status, review_id, executed_at, event_sequence
                FROM review_cycle_status_projection WHERE cycle_id = %s
                """,
                (cycle_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return ReviewCycleStatusProjection(
                cycle_id=row[0], status=row[1], review_id=row[2],
                executed_at=row[3], event_sequence=row[4],
            )

    def list_by_status(self, status: str) -> List[ReviewCycleStatusProjection]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT cycle_id, status, review_id, executed_at, event_sequence
                FROM review_cycle_status_projection WHERE status = %s ORDER BY cycle_id
                """,
                (status,)
            )
            rows = cur.fetchall()
            return [
                ReviewCycleStatusProjection(
                    cycle_id=r[0], status=r[1], review_id=r[2],
                    executed_at=r[3], event_sequence=r[4],
                )
                for r in rows
            ]

    def upsert_created(self, cycle_id: str, event_sequence: int) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_cycle_status_projection (cycle_id, status, event_sequence)
                VALUES (%s, 'CREATED', %s)
                ON CONFLICT (cycle_id) DO NOTHING
                """,
                (cycle_id, event_sequence)
            )

    def upsert_due(self, cycle_id: str, event_sequence: int) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE review_cycle_status_projection
                SET status = 'DUE', event_sequence = %s
                WHERE cycle_id = %s AND event_sequence < %s
                """,
                (event_sequence, cycle_id, event_sequence)
            )

    def upsert_overdue(self, cycle_id: str, event_sequence: int) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE review_cycle_status_projection
                SET status = 'OVERDUE', event_sequence = %s
                WHERE cycle_id = %s AND event_sequence < %s
                """,
                (event_sequence, cycle_id, event_sequence)
            )

    def upsert_executed(self, cycle_id: str, review_id: str, executed_at: datetime, event_sequence: int) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE review_cycle_status_projection
                SET status = 'EXECUTED', review_id = %s, executed_at = %s, event_sequence = %s
                WHERE cycle_id = %s AND event_sequence < %s
                """,
                (review_id, executed_at, event_sequence, cycle_id, event_sequence)
            )

    def rebuild(self) -> None:
        """Rebuilds cycle status projection from event journal.

        Replay sources:
        - ReviewCycleCreatedEvent (creates CREATED rows)
        - ReviewDueEvent (updates to DUE)
        - ReviewOverdueEvent (updates to OVERDUE)
        - ReviewExecutedEvent (updates to EXECUTED)

        Deterministic: same events always produce same projection state.
        """
        with self.conn.cursor() as cur:
            # 1. Truncate projection
            cur.execute("TRUNCATE TABLE review_cycle_status_projection")

            # 2. Replay ReviewCycleCreatedEvent
            cur.execute(
                """
                SELECT payload->>'cycle_id' as cycle_id,
                       (payload->>'event_sequence')::bigint as event_sequence
                FROM event_journal
                WHERE event_type = 'ReviewCycleCreatedEvent'
                ORDER BY sequence_id
                """
            )
            created_rows = cur.fetchall()

            for row in created_rows:
                cycle_id = row[0]
                event_sequence = row[1] or 0
                cur.execute(
                    """
                    INSERT INTO review_cycle_status_projection (cycle_id, status, event_sequence)
                    VALUES (%s, 'CREATED', %s)
                    ON CONFLICT (cycle_id) DO NOTHING
                    """,
                    (cycle_id, event_sequence)
                )

            # 3. Replay ReviewDueEvent
            cur.execute(
                """
                SELECT payload->>'cycle_id' as cycle_id,
                       (payload->>'event_sequence')::bigint as event_sequence
                FROM event_journal
                WHERE event_type = 'ReviewDueEvent'
                ORDER BY sequence_id
                """
            )
            due_rows = cur.fetchall()

            for row in due_rows:
                cycle_id = row[0]
                event_sequence = row[1] or 0
                cur.execute(
                    """
                    UPDATE review_cycle_status_projection
                    SET status = 'DUE', event_sequence = %s
                    WHERE cycle_id = %s AND event_sequence < %s
                    """,
                    (event_sequence, cycle_id, event_sequence)
                )

            # 4. Replay ReviewOverdueEvent
            cur.execute(
                """
                SELECT payload->>'cycle_id' as cycle_id,
                       (payload->>'event_sequence')::bigint as event_sequence
                FROM event_journal
                WHERE event_type = 'ReviewOverdueEvent'
                ORDER BY sequence_id
                """
            )
            overdue_rows = cur.fetchall()

            for row in overdue_rows:
                cycle_id = row[0]
                event_sequence = row[1] or 0
                cur.execute(
                    """
                    UPDATE review_cycle_status_projection
                    SET status = 'OVERDUE', event_sequence = %s
                    WHERE cycle_id = %s AND event_sequence < %s
                    """,
                    (event_sequence, cycle_id, event_sequence)
                )

            # 5. Replay ReviewExecutedEvent
            cur.execute(
                """
                SELECT payload->>'cycle_id' as cycle_id,
                       payload->>'review_id' as review_id,
                       (payload->>'executed_at')::timestamptz as executed_at,
                       (payload->>'event_sequence')::bigint as event_sequence
                FROM event_journal
                WHERE event_type = 'ReviewExecutedEvent'
                ORDER BY sequence_id
                """
            )
            executed_rows = cur.fetchall()

            for row in executed_rows:
                cycle_id = row[0]
                review_id = row[1]
                executed_at = row[2]
                event_sequence = row[3] or 0
                cur.execute(
                    """
                    UPDATE review_cycle_status_projection
                    SET status = 'EXECUTED', review_id = %s, executed_at = %s, event_sequence = %s
                    WHERE cycle_id = %s AND event_sequence < %s
                    """,
                    (review_id, executed_at, event_sequence, cycle_id, event_sequence)
                )
