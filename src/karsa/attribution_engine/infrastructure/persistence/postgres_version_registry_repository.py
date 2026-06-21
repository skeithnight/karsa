"""PostgresAttributionVersionRegistryRepository — Sprint-09.

Mutable governance repository. ADR-102, ADR-104.
"""
from typing import List, Optional
from datetime import datetime
import psycopg

from karsa.attribution_engine.infrastructure.repositories.attribution_version_registry_repository import (
    AttributionVersionRegistryRepository, VersionRegistryEntry,
)


class PostgresAttributionVersionRegistryRepository(AttributionVersionRegistryRepository):
    def __init__(self, conn):
        self.conn = conn

    def save(self, entry: VersionRegistryEntry) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO attribution_version_registry (
                    version_id, evaluation_id, algorithm_version,
                    attribution_id, attribution_status, superseded_by,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    entry.version_id,
                    entry.evaluation_id,
                    entry.algorithm_version,
                    entry.attribution_id,
                    entry.attribution_status,
                    entry.superseded_by,
                    entry.created_at,
                    entry.updated_at,
                )
            )

    def get_canonical(self, evaluation_id: str) -> Optional[VersionRegistryEntry]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM attribution_version_registry WHERE evaluation_id = %s AND attribution_status = 'CANONICAL'",
                (evaluation_id,)
            )
            row = cur.fetchone()
            return self._row_to_entry(row) if row else None

    def get_by_evaluation_and_algorithm(self, evaluation_id: str, algorithm_version: str) -> Optional[VersionRegistryEntry]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM attribution_version_registry WHERE evaluation_id = %s AND algorithm_version = %s",
                (evaluation_id, algorithm_version)
            )
            row = cur.fetchone()
            return self._row_to_entry(row) if row else None

    def supersede_previous(self, evaluation_id: str, new_algorithm_version: str, new_attribution_id: str) -> None:
        """Mark previous canonical as SUPERSEDED. ADR-102."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE attribution_version_registry
                SET attribution_status = 'SUPERSEDED',
                    superseded_by = %s,
                    updated_at = NOW()
                WHERE evaluation_id = %s AND attribution_status = 'CANONICAL'
                """,
                (new_attribution_id, evaluation_id)
            )

    def list_by_evaluation(self, evaluation_id: str) -> List[VersionRegistryEntry]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM attribution_version_registry WHERE evaluation_id = %s ORDER BY created_at",
                (evaluation_id,)
            )
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def _row_to_entry(self, row) -> VersionRegistryEntry:
        return VersionRegistryEntry(
            version_id=row[0],
            evaluation_id=row[1],
            algorithm_version=row[2],
            attribution_id=row[3],
            attribution_status=row[4],
            superseded_by=row[5],
            created_at=row[6],
            updated_at=row[7],
        )
