"""PostgresCapabilityScoreHistoryRepository -- Sprint-11. ADR-132, ADR-136."""

import json
from typing import List

import psycopg

from karsa.capability_engine.domain.value_objects.score_history_entry import (
    ScoreHistoryEntry,
)
from karsa.capability_engine.infrastructure.repositories.capability_score_history_repository import (
    CapabilityScoreHistoryRepository,
)

TABLE = "capability_score_history"


class PostgresCapabilityScoreHistoryRepository(CapabilityScoreHistoryRepository):
    """Append-only Postgres repository for score history.

    ADR-132: History in separate table, not embedded in aggregate.
    ADR-136: evaluation_sequence ordering enforced via unique constraint.
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def append(self, entry: ScoreHistoryEntry) -> bool:
        sql = f"""
            INSERT INTO {TABLE} (
                capability_family_id, evaluation_id, evaluation_sequence,
                capability_version_id, score, components,
                algorithm_version, recorded_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (capability_family_id, evaluation_sequence) DO NOTHING
        """
        with self.conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    entry.capability_family_id,
                    entry.evaluation_id,
                    entry.evaluation_sequence,
                    entry.capability_version_id,
                    entry.score,
                    json.dumps(
                        [
                            {
                                "component_name": c.component_name,
                                "component_score": c.component_score,
                                "weight": c.weight,
                                "evaluation_count": c.evaluation_count,
                                "confidence": c.confidence,
                            }
                            for c in entry.components
                        ]
                    ),
                    entry.algorithm_version,
                    entry.recorded_at,
                ),
            )
            return cur.rowcount > 0

    def get_by_family(
        self, capability_family_id: str
    ) -> List[ScoreHistoryEntry]:
        sql = f"""
            SELECT * FROM {TABLE}
            WHERE capability_family_id = %s
            ORDER BY evaluation_sequence ASC
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (capability_family_id,))
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def get_last_sequence(self, capability_family_id: str) -> int:
        sql = f"""
            SELECT COALESCE(MAX(evaluation_sequence), 0)
            FROM {TABLE}
            WHERE capability_family_id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (capability_family_id,))
            row = cur.fetchone()
            return row[0] if row else 0

    def get_by_family_and_version(
        self, capability_family_id: str, capability_version_id: str
    ) -> List[ScoreHistoryEntry]:
        sql = f"""
            SELECT * FROM {TABLE}
            WHERE capability_family_id = %s
              AND capability_version_id = %s
            ORDER BY evaluation_sequence ASC
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (capability_family_id, capability_version_id))
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def _row_to_entry(self, row: tuple) -> ScoreHistoryEntry:
        from karsa.capability_engine.domain.value_objects.capability_score_component import (
            CapabilityScoreComponent,
        )

        components_raw = (
            json.loads(row[6]) if isinstance(row[6], str) else row[6]
        )
        components = [
            CapabilityScoreComponent(**c) for c in components_raw
        ]
        return ScoreHistoryEntry(
            capability_family_id=row[0],
            evaluation_id=row[1],
            evaluation_sequence=row[2],
            capability_version_id=row[3],
            score=row[4],
            algorithm_version=row[5],
            components=components,
            recorded_at=row[7],
        )
