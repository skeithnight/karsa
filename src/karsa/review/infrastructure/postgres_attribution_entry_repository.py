"""PostgresAttributionEntryRepository — Sprint-07 Wave-2C."""
import json
from typing import List
from datetime import datetime

import psycopg

from karsa.review.domain.aggregates.attribution_entry import AttributionEntry
from karsa.review.domain.value_objects.review_verdict import AttributionDimension, AttributionType
from karsa.review.domain.repositories.attribution_entry_repository import AttributionEntryRepository
from karsa.review.infrastructure.jsonb_serializers import to_jsonb


class PostgresAttributionEntryRepository(AttributionEntryRepository):
    def __init__(self, conn):
        self.conn = conn

    def save_entry(self, entry: AttributionEntry) -> None:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO attribution_entries (
                        attribution_id, review_id, dimension, target_urn,
                        contribution_bps, contribution_pct, attribution_type,
                        evidence, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        entry.attribution_id,
                        entry.review_id,
                        entry.dimension.value,
                        entry.target_urn,
                        entry.contribution_bps,
                        entry.contribution_pct,
                        entry.attribution_type.value,
                        to_jsonb(entry.evidence),
                        entry.created_at,
                    )
                )
        except psycopg.errors.RaiseException as e:
            raise ValueError(str(e))

    def save_entries(self, entries: List[AttributionEntry]) -> None:
        if not entries:
            return
        try:
            with self.conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO attribution_entries (
                        attribution_id, review_id, dimension, target_urn,
                        contribution_bps, contribution_pct, attribution_type,
                        evidence, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            e.attribution_id, e.review_id, e.dimension.value,
                            e.target_urn, e.contribution_bps, e.contribution_pct,
                            e.attribution_type.value, to_jsonb(e.evidence), e.created_at,
                        )
                        for e in entries
                    ]
                )
        except psycopg.errors.RaiseException as e:
            raise ValueError(str(e))

    def get_entries_by_review_id(self, review_id: str) -> List[AttributionEntry]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT attribution_id, review_id, dimension, target_urn,
                       contribution_bps, contribution_pct, attribution_type,
                       evidence, created_at
                FROM attribution_entries WHERE review_id = %s ORDER BY created_at
                """,
                (review_id,)
            )
            rows = cur.fetchall()
            return [self._row_to_aggregate(r) for r in rows]

    def get_entries_by_target_urn(self, target_urn: str) -> List[AttributionEntry]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT attribution_id, review_id, dimension, target_urn,
                       contribution_bps, contribution_pct, attribution_type,
                       evidence, created_at
                FROM attribution_entries WHERE target_urn = %s ORDER BY created_at DESC
                """,
                (target_urn,)
            )
            rows = cur.fetchall()
            return [self._row_to_aggregate(r) for r in rows]

    def get_entries_by_dimension(
        self, review_id: str, dimension: AttributionDimension
    ) -> List[AttributionEntry]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT attribution_id, review_id, dimension, target_urn,
                       contribution_bps, contribution_pct, attribution_type,
                       evidence, created_at
                FROM attribution_entries WHERE review_id = %s AND dimension = %s ORDER BY created_at
                """,
                (review_id, dimension.value)
            )
            rows = cur.fetchall()
            return [self._row_to_aggregate(r) for r in rows]

    def _row_to_aggregate(self, row) -> AttributionEntry:
        return AttributionEntry(
            attribution_id=row[0],
            review_id=row[1],
            dimension=AttributionDimension(row[2]),
            target_urn=row[3],
            contribution_bps=float(row[4]),
            contribution_pct=float(row[5]),
            attribution_type=AttributionType(row[6]),
            evidence=row[7] if isinstance(row[7], dict) else json.loads(row[7]) if row[7] else {},
            created_at=row[8],
        )
