"""PostgresCapabilityScoreProjectionRepository — Sprint-07 Wave-2C."""
from typing import Optional, List
from datetime import datetime

from karsa.review.domain.repositories.capability_score_projection_repository import (
    CapabilityScoreProjectionRepository, CapabilityScoreProjection,
)


class PostgresCapabilityScoreProjectionRepository(CapabilityScoreProjectionRepository):
    def __init__(self, conn):
        self.conn = conn

    def get_by_target_urn(self, target_urn: str) -> Optional[CapabilityScoreProjection]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT target_urn, target_type, current_score, current_confidence,
                       adjustment_count, last_updated
                FROM capability_score_projection WHERE target_urn = %s
                """,
                (target_urn,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return CapabilityScoreProjection(
                target_urn=row[0],
                target_type=row[1],
                current_score=float(row[2]),
                current_confidence=float(row[3]),
                adjustment_count=row[4],
                last_updated=row[5],
            )

    def list_all(self) -> List[CapabilityScoreProjection]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT target_urn, target_type, current_score, current_confidence,
                       adjustment_count, last_updated
                FROM capability_score_projection ORDER BY current_score DESC
                """
            )
            rows = cur.fetchall()
            return [
                CapabilityScoreProjection(
                    target_urn=r[0], target_type=r[1],
                    current_score=float(r[2]), current_confidence=float(r[3]),
                    adjustment_count=r[4], last_updated=r[5],
                )
                for r in rows
            ]

    def upsert(
        self,
        target_urn: str,
        target_type: str,
        score_delta: float,
        confidence_delta: float,
        adjustment_count_delta: int = 1,
    ) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO capability_score_projection (
                    target_urn, target_type, current_score, current_confidence,
                    adjustment_count, last_updated
                ) VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (target_urn) DO UPDATE SET
                    current_score = capability_score_projection.current_score + EXCLUDED.current_score,
                    current_confidence = capability_score_projection.current_confidence + EXCLUDED.current_confidence,
                    adjustment_count = capability_score_projection.adjustment_count + EXCLUDED.adjustment_count,
                    last_updated = NOW()
                """,
                (target_urn, target_type, score_delta, confidence_delta, adjustment_count_delta)
            )

    def rebuild(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE capability_score_projection")
            cur.execute(
                """
                INSERT INTO capability_score_projection (
                    target_urn, target_type, current_score, current_confidence,
                    adjustment_count, last_updated
                )
                SELECT
                    target_urn,
                    target_type,
                    SUM(score_delta) as current_score,
                    SUM(confidence_delta) as current_confidence,
                    COUNT(*) as adjustment_count,
                    MAX(created_at) as last_updated
                FROM capability_score_adjustments
                GROUP BY target_urn, target_type
                """
            )
