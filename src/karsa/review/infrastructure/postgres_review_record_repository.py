"""PostgresReviewRecordRepository — Sprint-07 Wave-2C."""
import json
from typing import Optional, List
from datetime import datetime

import psycopg

from karsa.review.domain.aggregates.review_record import ReviewRecord
from karsa.review.domain.value_objects.review_verdict import ReviewType, ReviewVerdict
from karsa.review.domain.value_objects.decision_snapshot import DecisionSnapshot
from karsa.review.domain.value_objects.actual_outcome_snapshot import ActualOutcomeSnapshot
from karsa.review.domain.value_objects.variance_analysis import VarianceAnalysis
from karsa.review.domain.repositories.review_record_repository import ReviewRecordRepository
from karsa.review.infrastructure.jsonb_serializers import (
    serialize_decision_snapshot, deserialize_decision_snapshot,
    serialize_actual_outcome, deserialize_actual_outcome,
    serialize_variance, deserialize_variance,
    to_jsonb,
)


class PostgresReviewRecordRepository(ReviewRecordRepository):
    def __init__(self, conn):
        self.conn = conn

    def save_record(self, record: ReviewRecord) -> None:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO review_records (
                        review_id, cycle_id, review_type, decision_snapshot,
                        actual_outcome, variance, verdict, rationale,
                        executed_at, executed_by, evidence_refs
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.review_id,
                        record.cycle_id,
                        record.review_type.value,
                        to_jsonb(serialize_decision_snapshot(record.decision_snapshot)),
                        to_jsonb(serialize_actual_outcome(record.actual_outcome)),
                        to_jsonb(serialize_variance(record.variance)),
                        record.verdict.value,
                        record.rationale,
                        record.executed_at,
                        record.executed_by,
                        to_jsonb(record.evidence_refs),
                    )
                )
        except psycopg.errors.RaiseException as e:
            raise ValueError(str(e))

    def get_record_by_id(self, review_id: str) -> Optional[ReviewRecord]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT review_id, cycle_id, review_type, decision_snapshot,
                       actual_outcome, variance, verdict, rationale,
                       executed_at, executed_by, evidence_refs
                FROM review_records WHERE review_id = %s
                """,
                (review_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_aggregate(row)

    def get_records_by_cycle_id(self, cycle_id: str) -> List[ReviewRecord]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT review_id, cycle_id, review_type, decision_snapshot,
                       actual_outcome, variance, verdict, rationale,
                       executed_at, executed_by, evidence_refs
                FROM review_records WHERE cycle_id = %s ORDER BY executed_at
                """,
                (cycle_id,)
            )
            rows = cur.fetchall()
            return [self._row_to_aggregate(r) for r in rows]

    def list_records(self, page: int = 1, size: int = 50) -> List[ReviewRecord]:
        offset = (page - 1) * size
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT review_id, cycle_id, review_type, decision_snapshot,
                       actual_outcome, variance, verdict, rationale,
                       executed_at, executed_by, evidence_refs
                FROM review_records ORDER BY executed_at DESC LIMIT %s OFFSET %s
                """,
                (size, offset)
            )
            rows = cur.fetchall()
            return [self._row_to_aggregate(r) for r in rows]

    def _row_to_aggregate(self, row) -> ReviewRecord:
        return ReviewRecord(
            review_id=row[0],
            cycle_id=row[1],
            review_type=ReviewType(row[2]),
            decision_snapshot=deserialize_decision_snapshot(row[3] if isinstance(row[3], dict) else json.loads(row[3])),
            actual_outcome=deserialize_actual_outcome(row[4] if isinstance(row[4], dict) else json.loads(row[4])),
            variance=deserialize_variance(row[5] if isinstance(row[5], dict) else json.loads(row[5])),
            verdict=ReviewVerdict(row[6]),
            rationale=row[7],
            executed_at=row[8],
            executed_by=row[9],
            evidence_refs=row[10] if isinstance(row[10], list) else json.loads(row[10]),
        )
