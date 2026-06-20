"""PostgresReviewCycleRepository — Sprint-07 Wave-2C."""
import json
from typing import Optional, List
from datetime import datetime

import psycopg

from karsa.review.domain.aggregates.review_cycle import ReviewCycle
from karsa.review.domain.value_objects.review_verdict import ReviewType
from karsa.review.domain.value_objects.decision_snapshot import DecisionSnapshot
from karsa.review.domain.value_objects.schedule_policy import SchedulePolicy
from karsa.review.domain.value_objects.review_template import ReviewTemplate
from karsa.review.domain.repositories.review_cycle_repository import ReviewCycleRepository
from karsa.review.infrastructure.jsonb_serializers import (
    serialize_decision_snapshot, deserialize_decision_snapshot,
    serialize_schedule_policy, deserialize_schedule_policy,
    serialize_review_template, deserialize_review_template,
    to_jsonb,
)


class PostgresReviewCycleRepository(ReviewCycleRepository):
    def __init__(self, conn):
        self.conn = conn

    def save_cycle(self, cycle: ReviewCycle) -> bool:
        """Saves a review cycle. Idempotent on decision_id.

        Returns True if the cycle was actually inserted (new row created).
        Returns False if a cycle already exists for this decision_id (ON CONFLICT DO NOTHING).

        The caller MUST check the return value before creating outbox events
        to prevent phantom event creation on concurrent races.
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO review_cycles (
                        cycle_id, decision_id, proposal_id, journal_ref,
                        review_type, decision_snapshot, schedule_policy,
                        review_template, eligibility_event_ref, created_at, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (decision_id) DO NOTHING
                    """,
                    (
                        cycle.cycle_id,
                        cycle.decision_id,
                        cycle.proposal_id,
                        cycle.journal_ref,
                        cycle.review_type.value,
                        to_jsonb(serialize_decision_snapshot(cycle.decision_snapshot)),
                        to_jsonb(serialize_schedule_policy(cycle.schedule_policy)),
                        to_jsonb(serialize_review_template(cycle.review_template)),
                        cycle.eligibility_event_ref,
                        cycle.created_at,
                        cycle.created_by,
                    )
                )
                return cur.rowcount > 0
        except psycopg.errors.RaiseException as e:
            raise ValueError(str(e))

    def get_cycle_by_id(self, cycle_id: str) -> Optional[ReviewCycle]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT cycle_id, decision_id, proposal_id, journal_ref,
                       review_type, decision_snapshot, schedule_policy,
                       review_template, eligibility_event_ref, created_at, created_by
                FROM review_cycles WHERE cycle_id = %s
                """,
                (cycle_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_aggregate(row)

    def get_cycle_by_decision_id(self, decision_id: str) -> Optional[ReviewCycle]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT cycle_id, decision_id, proposal_id, journal_ref,
                       review_type, decision_snapshot, schedule_policy,
                       review_template, eligibility_event_ref, created_at, created_by
                FROM review_cycles WHERE decision_id = %s
                """,
                (decision_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_aggregate(row)

    def get_cycle_by_eligibility_ref(self, eligibility_event_ref: str) -> Optional[ReviewCycle]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT cycle_id, decision_id, proposal_id, journal_ref,
                       review_type, decision_snapshot, schedule_policy,
                       review_template, eligibility_event_ref, created_at, created_by
                FROM review_cycles WHERE eligibility_event_ref = %s
                """,
                (eligibility_event_ref,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_aggregate(row)

    def list_cycles(self, page: int = 1, size: int = 50) -> List[ReviewCycle]:
        offset = (page - 1) * size
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT cycle_id, decision_id, proposal_id, journal_ref,
                       review_type, decision_snapshot, schedule_policy,
                       review_template, eligibility_event_ref, created_at, created_by
                FROM review_cycles ORDER BY created_at DESC LIMIT %s OFFSET %s
                """,
                (size, offset)
            )
            rows = cur.fetchall()
            return [self._row_to_aggregate(r) for r in rows]

    def _row_to_aggregate(self, row) -> ReviewCycle:
        return ReviewCycle(
            cycle_id=row[0],
            decision_id=row[1],
            proposal_id=row[2],
            journal_ref=row[3],
            review_type=ReviewType(row[4]),
            decision_snapshot=deserialize_decision_snapshot(row[5] if isinstance(row[5], dict) else json.loads(row[5])),
            schedule_policy=deserialize_schedule_policy(row[6] if isinstance(row[6], dict) else json.loads(row[6])),
            review_template=deserialize_review_template(row[7] if isinstance(row[7], dict) else json.loads(row[7])),
            eligibility_event_ref=row[8],
            created_at=row[9],
            created_by=row[10],
        )
