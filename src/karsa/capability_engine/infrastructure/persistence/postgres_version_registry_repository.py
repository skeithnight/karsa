"""PostgresCapabilityEvolutionVersionRegistryRepository -- Sprint-11. ADR-133."""

from datetime import datetime
from typing import List, Optional

import psycopg

from karsa.capability_engine.infrastructure.repositories.capability_evolution_version_registry_repository import (
    CapabilityEvolutionVersionRegistryRepository,
    EvolutionVersionRegistryEntry,
)

TABLE = "capability_evolution_version_registry"


class PostgresCapabilityEvolutionVersionRegistryRepository(
    CapabilityEvolutionVersionRegistryRepository
):
    """Mutable Postgres repository for evolution canonical governance.

    ADR-133: Exactly one CANONICAL per
    (capability_family_id, evaluation_id, trigger_type).
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def save(self, entry: EvolutionVersionRegistryEntry) -> None:
        sql = f"""
            INSERT INTO {TABLE} (
                version_id, capability_family_id, evaluation_id,
                trigger_type, evolution_id, evolution_status,
                superseded_by, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with self.conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    entry.version_id,
                    entry.capability_family_id,
                    entry.evaluation_id,
                    entry.trigger_type,
                    entry.evolution_id,
                    entry.evolution_status,
                    entry.superseded_by,
                    entry.created_at,
                    entry.updated_at,
                ),
            )

    def get_canonical(
        self,
        capability_family_id: str,
        evaluation_id: str,
        trigger_type: str,
    ) -> Optional[EvolutionVersionRegistryEntry]:
        sql = f"""
            SELECT * FROM {TABLE}
            WHERE capability_family_id = %s
              AND evaluation_id = %s
              AND trigger_type = %s
              AND evolution_status = 'CANONICAL'
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (capability_family_id, evaluation_id, trigger_type))
            row = cur.fetchone()
            return self._row_to_entry(row) if row else None

    def get_by_family_and_evaluation(
        self, capability_family_id: str, evaluation_id: str
    ) -> List[EvolutionVersionRegistryEntry]:
        sql = f"""
            SELECT * FROM {TABLE}
            WHERE capability_family_id = %s AND evaluation_id = %s
            ORDER BY created_at DESC
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (capability_family_id, evaluation_id))
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def supersede_previous(
        self,
        capability_family_id: str,
        evaluation_id: str,
        trigger_type: str,
        new_evolution_id: str,
    ) -> None:
        sql = f"""
            UPDATE {TABLE}
            SET evolution_status = 'SUPERSEDED',
                superseded_by = %s,
                updated_at = NOW()
            WHERE capability_family_id = %s
              AND evaluation_id = %s
              AND trigger_type = %s
              AND evolution_status = 'CANONICAL'
        """
        with self.conn.cursor() as cur:
            cur.execute(
                sql,
                (new_evolution_id, capability_family_id, evaluation_id, trigger_type),
            )

    def list_by_family(
        self, capability_family_id: str
    ) -> List[EvolutionVersionRegistryEntry]:
        sql = f"""
            SELECT * FROM {TABLE}
            WHERE capability_family_id = %s
            ORDER BY created_at DESC
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (capability_family_id,))
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def _row_to_entry(self, row: tuple) -> EvolutionVersionRegistryEntry:
        return EvolutionVersionRegistryEntry(
            version_id=row[0],
            capability_family_id=row[1],
            evaluation_id=row[2],
            trigger_type=row[3],
            evolution_id=row[4],
            evolution_status=row[5],
            superseded_by=row[6],
            created_at=row[7],
            updated_at=row[8],
        )
