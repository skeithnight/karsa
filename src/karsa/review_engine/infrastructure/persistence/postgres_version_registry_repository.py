"""PostgresReviewVersionRegistryRepository — Sprint-10.

Mutable governance repository. ADR-107.
"""
from typing import List, Optional
from datetime import datetime
import psycopg

from karsa.review_engine.infrastructure.repositories.review_version_registry_repository import (
    ReviewVersionRegistryRepository, VersionRegistryEntry,
)


class PostgresReviewVersionRegistryRepository(ReviewVersionRegistryRepository):
    def __init__(self, conn):
        self.conn = conn

    def save(self, entry: VersionRegistryEntry) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_version_registry (
                    version_id, evaluation_id, review_type, review_version,
                    review_id, review_status, superseded_by,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    entry.version_id,
                    entry.evaluation_id,
                    entry.review_type,
                    entry.review_version,
                    entry.review_id,
                    entry.review_status,
                    entry.superseded_by,
                    entry.created_at,
                    entry.updated_at,
                )
            )

    def get_canonical(self, evaluation_id: str, review_type: str) -> Optional[VersionRegistryEntry]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM review_version_registry WHERE evaluation_id = %s AND review_type = %s AND review_status = 'CANONICAL'",
                (evaluation_id, review_type)
            )
            row = cur.fetchone()
            return self._row_to_entry(row) if row else None

    def get_by_evaluation_and_version(self, evaluation_id: str, review_type: str, review_version: str) -> Optional[VersionRegistryEntry]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM review_version_registry WHERE evaluation_id = %s AND review_type = %s AND review_version = %s",
                (evaluation_id, review_type, review_version)
            )
            row = cur.fetchone()
            return self._row_to_entry(row) if row else None

    def supersede_previous(self, evaluation_id: str, review_type: str, new_review_id: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE review_version_registry
                SET review_status = 'SUPERSEDED',
                    superseded_by = %s,
                    updated_at = NOW()
                WHERE evaluation_id = %s AND review_type = %s AND review_status = 'CANONICAL'
                """,
                (new_review_id, evaluation_id, review_type)
            )

    def list_by_evaluation(self, evaluation_id: str) -> List[VersionRegistryEntry]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM review_version_registry WHERE evaluation_id = %s ORDER BY created_at",
                (evaluation_id,)
            )
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def _row_to_entry(self, row) -> VersionRegistryEntry:
        return VersionRegistryEntry(
            version_id=row[0],
            evaluation_id=row[1],
            review_type=row[2],
            review_version=row[3],
            review_id=row[4],
            review_status=row[5],
            superseded_by=row[6],
            created_at=row[7],
            updated_at=row[8],
        )
