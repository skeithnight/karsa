"""PostgresCapabilityScoreAdjustmentRepository — Sprint-07 Wave-2C."""
from typing import List
from datetime import datetime

import psycopg

from karsa.review.domain.aggregates.capability_score_adjustment import CapabilityScoreAdjustment
from karsa.review.domain.repositories.capability_score_adjustment_repository import CapabilityScoreAdjustmentRepository


class PostgresCapabilityScoreAdjustmentRepository(CapabilityScoreAdjustmentRepository):
    def __init__(self, conn):
        self.conn = conn

    def save_adjustment(self, adjustment: CapabilityScoreAdjustment) -> None:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO capability_score_adjustments (
                        adjustment_id, target_urn, target_type,
                        score_delta, confidence_delta, review_id,
                        rationale, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        adjustment.adjustment_id,
                        adjustment.target_urn,
                        adjustment.target_type,
                        adjustment.score_delta,
                        adjustment.confidence_delta,
                        adjustment.review_id,
                        adjustment.rationale,
                        adjustment.created_at,
                    )
                )
        except psycopg.errors.RaiseException as e:
            raise ValueError(str(e))

    def save_adjustments(self, adjustments: List[CapabilityScoreAdjustment]) -> None:
        if not adjustments:
            return
        try:
            with self.conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO capability_score_adjustments (
                        adjustment_id, target_urn, target_type,
                        score_delta, confidence_delta, review_id,
                        rationale, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            a.adjustment_id, a.target_urn, a.target_type,
                            a.score_delta, a.confidence_delta, a.review_id,
                            a.rationale, a.created_at,
                        )
                        for a in adjustments
                    ]
                )
        except psycopg.errors.RaiseException as e:
            raise ValueError(str(e))

    def get_adjustments_by_review_id(self, review_id: str) -> List[CapabilityScoreAdjustment]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT adjustment_id, target_urn, target_type,
                       score_delta, confidence_delta, review_id,
                       rationale, created_at
                FROM capability_score_adjustments WHERE review_id = %s ORDER BY created_at
                """,
                (review_id,)
            )
            rows = cur.fetchall()
            return [self._row_to_aggregate(r) for r in rows]

    def get_adjustments_by_target_urn(self, target_urn: str) -> List[CapabilityScoreAdjustment]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT adjustment_id, target_urn, target_type,
                       score_delta, confidence_delta, review_id,
                       rationale, created_at
                FROM capability_score_adjustments WHERE target_urn = %s ORDER BY created_at
                """,
                (target_urn,)
            )
            rows = cur.fetchall()
            return [self._row_to_aggregate(r) for r in rows]

    def _row_to_aggregate(self, row) -> CapabilityScoreAdjustment:
        return CapabilityScoreAdjustment(
            adjustment_id=row[0],
            target_urn=row[1],
            target_type=row[2],
            score_delta=float(row[3]),
            confidence_delta=float(row[4]),
            review_id=row[5],
            rationale=row[6],
            created_at=row[7],
        )
