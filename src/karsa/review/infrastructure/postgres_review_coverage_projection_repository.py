"""PostgresReviewCoverageProjectionRepository — Sprint-07 Wave-2C."""
from typing import Optional, List
from datetime import datetime

from karsa.review.domain.repositories.review_coverage_projection_repository import (
    ReviewCoverageProjectionRepository, ReviewCoverageProjection,
)


class PostgresReviewCoverageProjectionRepository(ReviewCoverageProjectionRepository):
    def __init__(self, conn):
        self.conn = conn

    def get_by_decision_id(self, decision_id: str) -> Optional[ReviewCoverageProjection]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT decision_id, proposal_id, cycle_id, eligible, review_type,
                       strategy_name, strategy_version, evaluation_reason,
                       review_status, review_due_date, executed_at, days_overdue, evaluated_at
                FROM review_coverage_projection WHERE decision_id = %s
                """,
                (decision_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_projection(row)

    def list_by_status(self, status: str) -> List[ReviewCoverageProjection]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT decision_id, proposal_id, cycle_id, eligible, review_type,
                       strategy_name, strategy_version, evaluation_reason,
                       review_status, review_due_date, executed_at, days_overdue, evaluated_at
                FROM review_coverage_projection WHERE review_status = %s ORDER BY evaluated_at DESC
                """,
                (status,)
            )
            rows = cur.fetchall()
            return [self._row_to_projection(r) for r in rows]

    def list_overdue(self) -> List[ReviewCoverageProjection]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT decision_id, proposal_id, cycle_id, eligible, review_type,
                       strategy_name, strategy_version, evaluation_reason,
                       review_status, review_due_date, executed_at, days_overdue, evaluated_at
                FROM review_coverage_projection WHERE review_status = 'OVERDUE' ORDER BY days_overdue DESC
                """
            )
            rows = cur.fetchall()
            return [self._row_to_projection(r) for r in rows]

    def upsert_from_eligibility(
        self,
        decision_id: str,
        eligible: bool,
        review_type: Optional[str],
        strategy_name: str,
        strategy_version: str,
        evaluation_reason: str,
        evaluated_at: datetime,
    ) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_coverage_projection (
                    decision_id, eligible, review_type, strategy_name,
                    strategy_version, evaluation_reason, review_status, evaluated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (decision_id) DO UPDATE SET
                    eligible = EXCLUDED.eligible,
                    review_type = EXCLUDED.review_type,
                    strategy_name = EXCLUDED.strategy_name,
                    strategy_version = EXCLUDED.strategy_version,
                    evaluation_reason = EXCLUDED.evaluation_reason,
                    evaluated_at = EXCLUDED.evaluated_at
                """,
                (
                    decision_id, eligible, review_type, strategy_name,
                    strategy_version, evaluation_reason,
                    'NO_REVIEW' if not eligible else 'PENDING',
                    evaluated_at,
                )
            )

    def update_status(
        self,
        decision_id: str,
        review_status: str,
        cycle_id: Optional[str] = None,
        review_due_date: Optional[datetime] = None,
        executed_at: Optional[datetime] = None,
        days_overdue: Optional[int] = None,
    ) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE review_coverage_projection SET
                    review_status = %s,
                    cycle_id = COALESCE(%s, cycle_id),
                    review_due_date = COALESCE(%s, review_due_date),
                    executed_at = COALESCE(%s, executed_at),
                    days_overdue = COALESCE(%s, days_overdue)
                WHERE decision_id = %s
                """,
                (review_status, cycle_id, review_due_date, executed_at, days_overdue, decision_id)
            )

    def rebuild(self) -> None:
        """Rebuilds coverage projection from event journal.

        Replay sources:
        - ReviewEligibilityEvaluatedEvent (creates coverage rows)
        - ReviewCycleCreatedEvent (updates cycle_id, review_due_date)
        - ReviewExecutedEvent (updates executed_at, status)

        Deterministic: same events always produce same projection state.
        """
        with self.conn.cursor() as cur:
            # 1. Truncate projection
            cur.execute("TRUNCATE TABLE review_coverage_projection")

            # 2. Replay ReviewEligibilityEvaluatedEvent
            cur.execute(
                """
                SELECT payload->>'decision_id' as decision_id,
                       (payload->>'eligible')::boolean as eligible,
                       payload->>'review_type' as review_type,
                       payload->>'strategy_name' as strategy_name,
                       payload->>'strategy_version' as strategy_version,
                       payload->>'evaluation_reason' as evaluation_reason,
                       (payload->>'evaluated_at')::timestamptz as evaluated_at
                FROM event_journal
                WHERE event_type = 'ReviewEligibilityEvaluatedEvent'
                ORDER BY sequence_id
                """
            )
            eligibility_rows = cur.fetchall()

            for row in eligibility_rows:
                decision_id = row[0]
                eligible = row[1]
                review_type = row[2]
                strategy_name = row[3]
                strategy_version = row[4]
                evaluation_reason = row[5]
                evaluated_at = row[6]

                cur.execute(
                    """
                    INSERT INTO review_coverage_projection (
                        decision_id, eligible, review_type, strategy_name,
                        strategy_version, evaluation_reason, review_status, evaluated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (decision_id) DO NOTHING
                    """,
                    (
                        decision_id, eligible, review_type, strategy_name,
                        strategy_version, evaluation_reason,
                        'NO_REVIEW' if not eligible else 'PENDING',
                        evaluated_at,
                    )
                )

            # 3. Replay ReviewCycleCreatedEvent — update cycle_id and review_due_date
            cur.execute(
                """
                SELECT payload->>'cycle_id' as cycle_id,
                       payload->>'decision_id' as decision_id,
                       (payload->'schedule_policy'->>'review_due_date')::timestamptz as review_due_date
                FROM event_journal
                WHERE event_type = 'ReviewCycleCreatedEvent'
                ORDER BY sequence_id
                """
            )
            cycle_rows = cur.fetchall()

            for row in cycle_rows:
                cycle_id = row[0]
                decision_id = row[1]
                review_due_date = row[2]

                cur.execute(
                    """
                    UPDATE review_coverage_projection
                    SET cycle_id = %s, review_due_date = %s, review_status = 'PENDING'
                    WHERE decision_id = %s
                    """,
                    (cycle_id, review_due_date, decision_id)
                )

            # 4. Replay ReviewExecutedEvent — update executed_at and status
            cur.execute(
                """
                SELECT payload->>'cycle_id' as cycle_id,
                       (payload->>'executed_at')::timestamptz as executed_at
                FROM event_journal
                WHERE event_type = 'ReviewExecutedEvent'
                ORDER BY sequence_id
                """
            )
            executed_rows = cur.fetchall()

            for row in executed_rows:
                cycle_id = row[0]
                executed_at = row[1]

                cur.execute(
                    """
                    UPDATE review_coverage_projection
                    SET review_status = 'EXECUTED', executed_at = %s
                    WHERE cycle_id = %s
                    """,
                    (executed_at, cycle_id)
                )

    def _row_to_projection(self, row) -> ReviewCoverageProjection:
        return ReviewCoverageProjection(
            decision_id=row[0],
            proposal_id=row[1],
            cycle_id=row[2],
            eligible=row[3],
            review_type=row[4],
            strategy_name=row[5],
            strategy_version=row[6],
            evaluation_reason=row[7],
            review_status=row[8],
            review_due_date=row[9],
            executed_at=row[10],
            days_overdue=row[11],
            evaluated_at=row[12],
        )
