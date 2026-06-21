"""PostgresCapabilityEvolutionProjectionRepository -- Sprint-11."""

from typing import Any, Dict, List, Optional

import psycopg

from karsa.capability_engine.infrastructure.repositories.capability_evolution_projection_repository import (
    CapabilityEvolutionProjectionRepository,
)

TABLE = "capability_evolution_projection"


class PostgresCapabilityEvolutionProjectionRepository(
    CapabilityEvolutionProjectionRepository
):
    """Read-only Postgres projection for capability evolution summaries."""

    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def get_evolution_summary(
        self, capability_family_id: str
    ) -> Optional[Dict[str, Any]]:
        sql = f"SELECT * FROM {TABLE} WHERE capability_family_id = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (capability_family_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_dict(cur, row)

    def get_evolution_by_evaluation(
        self, evaluation_id: str
    ) -> List[Dict[str, Any]]:
        sql = f"SELECT * FROM {TABLE} WHERE evaluation_id = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (evaluation_id,))
            return [self._row_to_dict(cur, row) for row in cur.fetchall()]

    def rebuild_all(self) -> None:
        raise NotImplementedError("rebuild_all belongs to Wave-6")

    def _row_to_dict(
        self, cursor: psycopg.Cursor, row: tuple
    ) -> Dict[str, Any]:
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
