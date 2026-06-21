"""PostgresCapabilityHealthScoreRepository -- Sprint-11. ADR-132."""

import json
from typing import List, Optional

import psycopg

from karsa.capability_engine.domain.aggregates.capability_health_score import (
    CapabilityHealthScore,
)
from karsa.capability_engine.domain.value_objects.capability_score_component import (
    CapabilityScoreComponent,
)
from karsa.capability_engine.infrastructure.repositories.capability_health_score_repository import (
    CapabilityHealthScoreRepository,
)

TABLE = "capability_health_scores"


class PostgresCapabilityHealthScoreRepository(CapabilityHealthScoreRepository):
    """Mutable Postgres repository with OCC for health score aggregates.

    ADR-132: Separate aggregate with version-based optimistic concurrency.
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def save(self, aggregate: CapabilityHealthScore) -> bool:
        sql = f"""
            INSERT INTO {TABLE} (
                health_score_id, capability_family_id, current_score,
                score_components, evaluation_count, last_evaluated_at,
                current_version_id, last_recorded_sequence,
                consecutive_low_scores, consecutive_high_scores,
                algorithm_version, aggregate_version,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (capability_family_id) DO UPDATE SET
                current_score = EXCLUDED.current_score,
                score_components = EXCLUDED.score_components,
                evaluation_count = EXCLUDED.evaluation_count,
                last_evaluated_at = EXCLUDED.last_evaluated_at,
                current_version_id = EXCLUDED.current_version_id,
                last_recorded_sequence = EXCLUDED.last_recorded_sequence,
                consecutive_low_scores = EXCLUDED.consecutive_low_scores,
                consecutive_high_scores = EXCLUDED.consecutive_high_scores,
                algorithm_version = EXCLUDED.algorithm_version,
                aggregate_version = EXCLUDED.aggregate_version,
                updated_at = EXCLUDED.updated_at
            WHERE {TABLE}.aggregate_version = EXCLUDED.aggregate_version - 1
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        aggregate.health_score_id,
                        aggregate.capability_family_id,
                        aggregate.current_score,
                        json.dumps(
                            [
                                {
                                    "component_name": c.component_name,
                                    "component_score": c.component_score,
                                    "weight": c.weight,
                                    "evaluation_count": c.evaluation_count,
                                    "confidence": c.confidence,
                                }
                                for c in aggregate.score_components
                            ]
                        ),
                        aggregate.evaluation_count,
                        aggregate.last_evaluated_at,
                        aggregate.current_version_id,
                        aggregate.last_recorded_sequence,
                        aggregate.consecutive_low_scores,
                        aggregate.consecutive_high_scores,
                        aggregate.algorithm_version,
                        aggregate.aggregate_version,
                        aggregate.created_at,
                        aggregate.updated_at,
                    ),
                )
                return cur.rowcount > 0
        except psycopg.errors.RaiseException as e:
            raise ValueError(str(e))

    def get_by_family_id(
        self, capability_family_id: str
    ) -> Optional[CapabilityHealthScore]:
        sql = f"SELECT * FROM {TABLE} WHERE capability_family_id = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (capability_family_id,))
            row = cur.fetchone()
            return self._row_to_aggregate(row) if row else None

    def list_by_score_range(
        self, min_score: float, max_score: float
    ) -> List[CapabilityHealthScore]:
        sql = f"""
            SELECT * FROM {TABLE}
            WHERE current_score BETWEEN %s AND %s
            ORDER BY current_score DESC
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (min_score, max_score))
            return [self._row_to_aggregate(row) for row in cur.fetchall()]

    def list_all(
        self, page: int = 1, size: int = 50
    ) -> List[CapabilityHealthScore]:
        offset = (page - 1) * size
        sql = f"""
            SELECT * FROM {TABLE}
            ORDER BY current_score DESC
            LIMIT %s OFFSET %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (size, offset))
            return [self._row_to_aggregate(row) for row in cur.fetchall()]

    def _row_to_aggregate(self, row: tuple) -> CapabilityHealthScore:
        components_raw = (
            json.loads(row[3]) if isinstance(row[3], str) else row[3]
        )
        components = [
            CapabilityScoreComponent(**c) for c in components_raw
        ]
        return CapabilityHealthScore(
            health_score_id=row[0],
            capability_family_id=row[1],
            current_score=row[2],
            score_components=components,
            evaluation_count=row[4],
            last_evaluated_at=row[5],
            current_version_id=row[6],
            last_recorded_sequence=row[7],
            consecutive_low_scores=row[8],
            consecutive_high_scores=row[9],
            algorithm_version=row[10],
            aggregate_version=row[11],
            created_at=row[12],
            updated_at=row[13],
        )
