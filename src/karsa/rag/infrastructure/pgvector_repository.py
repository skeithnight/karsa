"""pgvector Repository — persistence for institutional memory embeddings.

Uses raw SQL via psycopg for pgvector operations (cosine similarity).
SQLAlchemy doesn't natively support pgvector operators.
"""
import json
import logging
from typing import List, Optional

import psycopg
from psycopg.rows import dict_row

from karsa.rag.domain.models import (
    InstitutionalMemoryEntry,
    EmbeddingEventType,
    SimilarityResult,
    RAGQuery,
)

logger = logging.getLogger(__name__)


class PostgresInstitutionalMemoryRepository:
    """Repository for ai_institutional_memory table with pgvector.

    Uses raw psycopg for vector operations (cosine distance `<=>`).
    """

    def __init__(self, dsn: str):
        self._dsn = dsn

    def _get_conn(self) -> psycopg.Connection:
        """Get a new connection (short-lived, per-operation)."""
        conn = psycopg.connect(self._dsn, row_factory=dict_row)
        # 5-second statement timeout for RAG queries — degrade gracefully on timeout
        conn.execute("SET statement_timeout = '5000'")
        return conn

    def write_entry(self, entry: InstitutionalMemoryEntry) -> None:
        """Write an embedding entry. Immutable — no updates."""
        if entry.embedding is None:
            raise ValueError("Cannot write entry without embedding")

        # Convert embedding list to pgvector format: '[0.1,0.2,...]'
        embedding_str = "[" + ",".join(str(f) for f in entry.embedding) + "]"

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO ai_institutional_memory
                    (id, event_type, reference_id, ticker, sector,
                     content_text, embedding, embedding_model, metadata, created_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s::vector, %s, %s, %s)
                """,
                (
                    entry.id,
                    entry.event_type.value,
                    entry.reference_id,
                    entry.ticker,
                    entry.sector,
                    entry.content_text,
                    embedding_str,
                    entry.embedding_model,
                    json.dumps(entry.metadata),
                    entry.created_at,
                ),
            )
            conn.commit()

    def write_entries_batch(self, entries: List[InstitutionalMemoryEntry]) -> int:
        """Batch write multiple entries. Returns count written."""
        if not entries:
            return 0

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                for entry in entries:
                    if entry.embedding is None:
                        continue
                    embedding_str = "[" + ",".join(str(f) for f in entry.embedding) + "]"
                    cur.execute(
                        """
                        INSERT INTO ai_institutional_memory
                            (id, event_type, reference_id, ticker, sector,
                             content_text, embedding, embedding_model, metadata, created_at)
                        VALUES
                            (%s, %s, %s, %s, %s, %s, %s::vector, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (
                            entry.id,
                            entry.event_type.value,
                            entry.reference_id,
                            entry.ticker,
                            entry.sector,
                            entry.content_text,
                            embedding_str,
                            entry.embedding_model,
                            json.dumps(entry.metadata),
                            entry.created_at,
                        ),
                    )
            conn.commit()
            return len(entries)

    def similarity_search(
        self,
        query_embedding: List[float],
        ticker: Optional[str] = None,
        sector: Optional[str] = None,
        top_k: int = 5,
        event_types: Optional[List[EmbeddingEventType]] = None,
        max_distance: float = 1.0,
    ) -> List[SimilarityResult]:
        """Cosine similarity search against pgvector.

        Args:
            query_embedding: 1536-dim query vector.
            ticker: Filter by ticker symbol.
            sector: Filter by sector.
            top_k: Number of results.
            event_types: Filter by event type.
            max_distance: Maximum cosine distance (0=identical, 2=opposite).

        Returns:
            List of SimilarityResult ordered by similarity (closest first).
        """
        embedding_str = "[" + ",".join(str(f) for f in query_embedding) + "]"

        # Build dynamic WHERE clause
        conditions = ["1=1"]
        params = [embedding_str]

        if ticker:
            conditions.append("ticker = %s")
            params.append(ticker)
        if sector:
            conditions.append("sector = %s")
            params.append(sector)
        if event_types:
            placeholders = ",".join(["%s"] * len(event_types))
            conditions.append(f"event_type IN ({placeholders})")
            params.extend([et.value for et in event_types])

        where_clause = " AND ".join(conditions)

        sql = f"""
            SELECT id, event_type, reference_id, ticker, sector,
                   content_text, metadata, created_at,
                   embedding <=> %s::vector AS distance
            FROM ai_institutional_memory
            WHERE {where_clause}
              AND embedding <=> %s::vector < %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        # embedding_str appears 3 times: SELECT distance, WHERE filter, ORDER BY
        params.extend([embedding_str, str(max_distance), embedding_str, str(top_k)])

        results = []
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            for row in rows:
                entry = InstitutionalMemoryEntry(
                    id=str(row["id"]),
                    event_type=EmbeddingEventType(row["event_type"]),
                    reference_id=str(row["reference_id"]),
                    ticker=row["ticker"],
                    sector=row["sector"],
                    content_text=row["content_text"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    created_at=row["created_at"],
                )
                results.append(SimilarityResult(
                    entry=entry,
                    similarity_score=float(row["distance"]),
                ))

        return results

    def count_entries(self) -> int:
        """Count total entries in the table."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM ai_institutional_memory"
            ).fetchone()
            return row["cnt"] if row else 0

    def count_by_event_type(self) -> dict:
        """Count entries grouped by event type."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT event_type, COUNT(*) AS cnt FROM ai_institutional_memory GROUP BY event_type"
            ).fetchall()
            return {row["event_type"]: row["cnt"] for row in rows}
