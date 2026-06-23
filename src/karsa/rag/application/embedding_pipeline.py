"""Embedding Pipeline Service — subscribes to domain events, generates
embeddings, and writes them to pgvector institutional memory.

Consumes: ThesisInvalidatedEvent, PostMortemCompletedEvent, NewsArticleEvent,
          ThesisApprovedEvent, ThesisRejectedEvent
Does not emit new events. Embedding is a terminal write.
"""
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from karsa.rag.domain.models import (
    InstitutionalMemoryEntry,
    EmbeddingRequest,
    EmbeddingEventType,
)
from karsa.rag.infrastructure.pgvector_repository import PostgresInstitutionalMemoryRepository

logger = logging.getLogger(__name__)


class EmbeddingPipelineService:
    """Subscribes to domain events, extracts text, generates embeddings,
    and writes to pgvector.

    Designed to run as a background worker consuming from the event bus.
    """

    def __init__(
        self,
        repository: PostgresInstitutionalMemoryRepository,
        generate_embedding: Callable,  # async callable: (text) -> List[float]
        embedding_model: str = "text-embedding-3-small",
    ):
        self._repo = repository
        self._generate_embedding = generate_embedding
        self._embedding_model = embedding_model
        self._processed_count = 0
        self._error_count = 0

    async def process_thesis_invalidated(
        self,
        thesis_id: str,
        ticker: str,
        sector: Optional[str],
        title: str,
        reasoning: str,
        invalidation_reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[InstitutionalMemoryEntry]:
        """Process a ThesisInvalidatedEvent — embed the thesis + invalidation reason."""
        content_text = (
            f"THESIS (INVALIDATED)\n"
            f"Ticker: {ticker}\n"
            f"Title: {title}\n"
            f"Reasoning: {reasoning}\n"
            f"Invalidation Reason: {invalidation_reason}"
        )
        return await self._embed_and_store(
            request=EmbeddingRequest(
                text=content_text,
                event_type=EmbeddingEventType.THESIS_INVALIDATED,
                reference_id=thesis_id,
                ticker=ticker,
                sector=sector,
                metadata={
                    **(metadata or {}),
                    "title": title,
                    "invalidation_reason": invalidation_reason,
                },
            ),
        )

    async def process_post_mortem_completed(
        self,
        post_mortem_id: str,
        ticker: str,
        sector: Optional[str],
        summary: str,
        outcome: str,  # "WIN" or "LOSS"
        pnl: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[InstitutionalMemoryEntry]:
        """Process a PostMortemCompletedEvent — embed the post-mortem summary."""
        content_text = (
            f"POST-MORTEM ({outcome})\n"
            f"Ticker: {ticker}\n"
            f"Summary: {summary}"
        )
        return await self._embed_and_store(
            request=EmbeddingRequest(
                text=content_text,
                event_type=EmbeddingEventType.POST_MORTEM_COMPLETED,
                reference_id=post_mortem_id,
                ticker=ticker,
                sector=sector,
                metadata={
                    **(metadata or {}),
                    "outcome": outcome,
                    "pnl": pnl,
                },
            ),
        )

    async def process_news_article(
        self,
        article_id: str,
        headline: str,
        tickers: List[str],
        url: str = "",
        sentiment_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[InstitutionalMemoryEntry]:
        """Process a news article — embed headline for each relevant ticker."""
        # Store one entry per ticker for filtered retrieval
        entry = None
        for ticker in tickers[:5]:  # Cap at 5 tickers to avoid explosion
            entry = await self._embed_and_store(
                request=EmbeddingRequest(
                    text=f"NEWS: {headline}",
                    event_type=EmbeddingEventType.NEWS_ARTICLE,
                    reference_id=article_id,
                    ticker=ticker,
                    metadata={
                        **(metadata or {}),
                        "headline": headline,
                        "url": url,
                        "sentiment_score": sentiment_score,
                    },
                ),
            )
        return entry

    async def process_thesis_decision(
        self,
        thesis_id: str,
        ticker: str,
        sector: Optional[str],
        side: str,
        title: str,
        reasoning: str,
        approved: bool,
        governance_reasoning: str = "",
        risk_flags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[InstitutionalMemoryEntry]:
        """Process a thesis approval/rejection for embedding."""
        status = "APPROVED" if approved else "REJECTED"
        content_text = (
            f"THESIS ({status})\n"
            f"Ticker: {ticker}\n"
            f"Side: {side}\n"
            f"Title: {title}\n"
            f"Reasoning: {reasoning}\n"
            f"Governance: {governance_reasoning}"
        )
        event_type = (
            EmbeddingEventType.THESIS_APPROVED
            if approved
            else EmbeddingEventType.THESIS_REJECTED
        )
        return await self._embed_and_store(
            request=EmbeddingRequest(
                text=content_text,
                event_type=event_type,
                reference_id=thesis_id,
                ticker=ticker,
                sector=sector,
                metadata={
                    **(metadata or {}),
                    "side": side,
                    "title": title,
                    "approved": approved,
                    "risk_flags": risk_flags or [],
                },
            ),
        )

    async def _embed_and_store(
        self,
        request: EmbeddingRequest,
    ) -> Optional[InstitutionalMemoryEntry]:
        """Generate embedding and write to pgvector."""
        try:
            embedding = await self._generate_embedding(request.text)
            entry = InstitutionalMemoryEntry(
                event_type=request.event_type,
                reference_id=request.reference_id,
                ticker=request.ticker,
                sector=request.sector,
                content_text=request.text,
                embedding=embedding,
                embedding_model=self._embedding_model,
                metadata=request.metadata,
            )
            await asyncio.to_thread(self._repo.write_entry, entry)
            self._processed_count += 1
            logger.info(
                f"Embedded {request.event_type.value} for {request.ticker or 'N/A'} "
                f"(total: {self._processed_count})"
            )
            return entry
        except Exception as e:
            self._error_count += 1
            logger.error(f"Embedding pipeline error: {e}")
            return None

    @property
    def processed_count(self) -> int:
        return self._processed_count

    @property
    def error_count(self) -> int:
        return self._error_count
