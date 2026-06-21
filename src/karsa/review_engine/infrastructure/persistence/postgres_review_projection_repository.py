"""PostgresReviewProjectionRepository — Sprint-10.

Read-only repository for review projections.
rebuild_all() belongs to Wave-6.
"""
from typing import List, Optional, Dict, Any

from karsa.review_engine.infrastructure.repositories.review_projection_repository import ReviewProjectionRepository


class PostgresReviewProjectionRepository(ReviewProjectionRepository):
    def __init__(self, conn):
        self.conn = conn

    def get_worker_review(self, target_urn: str) -> Optional[Dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM worker_review_projection WHERE target_urn = %s",
                (target_urn,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "target_urn": row[0],
                "total_reviews": row[1],
                "avg_quality_score": float(row[2]),
                "total_findings": row[3],
                "total_recommendations": row[4],
                "last_reviewed": row[5].isoformat() if row[5] else None,
            }

    def get_thesis_review(self, thesis_urn: str) -> Optional[Dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM thesis_review_projection WHERE thesis_urn = %s",
                (thesis_urn,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "thesis_urn": row[0],
                "total_reviews": row[1],
                "avg_quality_score": float(row[2]),
                "last_reviewed": row[3].isoformat() if row[3] else None,
            }

    def get_capability_gaps(self, target_urn: str) -> List[Dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM capability_gap_projection WHERE target_urn = %s ORDER BY identified_at DESC",
                (target_urn,)
            )
            return [
                {
                    "target_urn": r[0],
                    "gap_type": r[1],
                    "severity": r[2],
                    "description": r[3],
                    "identified_at": r[4].isoformat() if r[4] else None,
                }
                for r in cur.fetchall()
            ]

    def rebuild_all(self) -> None:
        """Rebuild all projections. Wave-6 implementation."""
        raise NotImplementedError("rebuild_all belongs to Wave-6")
