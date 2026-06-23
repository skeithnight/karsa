"""Context Retrieval Service — RAG queries against pgvector institutional memory.

Given a RAG query (ticker, sector, query text), generates an embedding
for the query text, performs cosine similarity search, and returns
formatted context for LLM prompts.
"""
import asyncio
import logging
from typing import Callable, List, Optional

from karsa.rag.domain.models import (
    RAGQuery,
    SimilarityResult,
    EmbeddingEventType,
    InstitutionalMemoryEntry,
)
from karsa.rag.infrastructure.pgvector_repository import PostgresInstitutionalMemoryRepository

logger = logging.getLogger(__name__)


class ContextRetrievalService:
    """Retrieves relevant institutional memory for RAG-enhanced LLM calls.

    Embeds the query text, performs pgvector cosine similarity search,
    and formats results as a context string for prompt injection.
    """

    def __init__(
        self,
        repository: PostgresInstitutionalMemoryRepository,
        generate_embedding: Callable,  # async callable: (text) -> List[float]
        default_top_k: int = 5,
        max_distance: float = 1.0,
        statement_timeout_ms: int = 5000,
    ):
        self._repo = repository
        self._generate_embedding = generate_embedding
        self._default_top_k = default_top_k
        self._max_distance = max_distance
        self._statement_timeout_ms = statement_timeout_ms

    async def retrieve_context(
        self,
        ticker: Optional[str] = None,
        sector: Optional[str] = None,
        query_text: str = "Recent market activity",
        top_k: Optional[int] = None,
        event_types: Optional[List[EmbeddingEventType]] = None,
    ) -> str:
        """Retrieve and format RAG context for a given query.

        Degrades gracefully: if embedding fails or no results found,
        returns empty string (does not block thesis generation).

        Args:
            ticker: Filter by ticker symbol.
            sector: Filter by sector.
            query_text: Natural language query for similarity search.
            top_k: Number of results (default: configured value).
            event_types: Filter by event type.

        Returns:
            Formatted context string for prompt injection, or empty string.
        """
        top_k = top_k or self._default_top_k

        try:
            # Generate embedding for the query text
            query_embedding = await self._generate_embedding(query_text)
        except Exception as e:
            logger.warning(f"RAG query embedding failed, degrading gracefully: {e}")
            return ""

        try:
            # Perform similarity search
            results = await asyncio.to_thread(
                self._repo.similarity_search,
                query_embedding=query_embedding,
                ticker=ticker,
                sector=sector,
                top_k=top_k,
                event_types=event_types,
                max_distance=self._max_distance,
            )
        except Exception as e:
            logger.warning(f"RAG similarity search failed, degrading gracefully: {e}")
            return ""

        if not results:
            return ""

        return self._format_context(results)

    async def retrieve_raw_results(
        self,
        ticker: Optional[str] = None,
        sector: Optional[str] = None,
        query_text: str = "Recent market activity",
        top_k: Optional[int] = None,
        event_types: Optional[List[EmbeddingEventType]] = None,
    ) -> List[SimilarityResult]:
        """Retrieve raw similarity results (for programmatic use)."""
        top_k = top_k or self._default_top_k

        try:
            query_embedding = await self._generate_embedding(query_text)
        except Exception as e:
            logger.warning(f"RAG query embedding failed: {e}")
            return []

        try:
            return await asyncio.to_thread(
                self._repo.similarity_search,
                query_embedding=query_embedding,
                ticker=ticker,
                sector=sector,
                top_k=top_k,
                event_types=event_types,
                max_distance=self._max_distance,
            )
        except Exception as e:
            logger.warning(f"RAG similarity search failed: {e}")
            return []

    def _format_context(self, results: List[SimilarityResult]) -> str:
        """Format similarity results into a context string for LLM prompts."""
        if not results:
            return ""

        lines = ["=== INSTITUTIONAL MEMORY (RAG Context) ==="]
        lines.append(f"Found {len(results)} relevant historical entries:\n")

        for i, result in enumerate(results, 1):
            entry = result.entry
            score = 1.0 - result.similarity_score  # Convert distance to similarity
            lines.append(f"--- Entry {i} (similarity: {score:.2f}) ---")
            lines.append(f"Type: {entry.event_type.value}")
            if entry.ticker:
                lines.append(f"Ticker: {entry.ticker}")
            if entry.sector:
                lines.append(f"Sector: {entry.sector}")

            # Include metadata highlights
            meta = entry.metadata
            if meta.get("outcome"):
                lines.append(f"Outcome: {meta['outcome']}")
            if meta.get("pnl") is not None:
                lines.append(f"PnL: {meta['pnl']:.2f}%")
            if meta.get("side"):
                lines.append(f"Side: {meta['side']}")
            if meta.get("risk_flags"):
                lines.append(f"Risk Flags: {', '.join(meta['risk_flags'])}")

            lines.append(f"Content: {entry.content_text[:500]}")
            lines.append("")

        lines.append("=== END INSTITUTIONAL MEMORY ===")
        return "\n".join(lines)
