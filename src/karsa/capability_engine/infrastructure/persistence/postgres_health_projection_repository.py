"""PostgresCapabilityHealthProjectionRepository -- Sprint-11."""

from typing import Any, Dict, List, Optional

import psycopg

from karsa.capability_engine.infrastructure.repositories.capability_health_projection_repository import (
    CapabilityHealthProjectionRepository,
)

TABLE = "capability_health_projection"


class PostgresCapabilityHealthProjectionRepository(
    CapabilityHealthProjectionRepository
):
    """Read-only Postgres projection for capability health scores."""

    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def get_health_score(
        self, capability_family_id: str
    ) -> Optional[Dict[str, Any]]:
        sql = f"SELECT * FROM {TABLE} WHERE capability_family_id = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (capability_family_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_dict(cur, row)

    def get_health_scores_above(
        self, threshold: float
    ) -> List[Dict[str, Any]]:
        sql = f"""
            SELECT * FROM {TABLE}
            WHERE current_score > %s
            ORDER BY current_score DESC
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (threshold,))
            return [self._row_to_dict(cur, row) for row in cur.fetchall()]

    def get_health_scores_below(
        self, threshold: float
    ) -> List[Dict[str, Any]]:
        sql = f"""
            SELECT * FROM {TABLE}
            WHERE current_score < %s
            ORDER BY current_score ASC
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (threshold,))
            return [self._row_to_dict(cur, row) for row in cur.fetchall()]

    def rebuild_all(self) -> None:
        raise NotImplementedError("rebuild_all belongs to Wave-6")

    def _row_to_dict(
        self, cursor: psycopg.Cursor, row: tuple
    ) -> Dict[str, Any]:
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
