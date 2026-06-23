"""Unit tests for Sprint-54: RAG domain models and context retrieval."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from karsa.rag.domain.models import (
    InstitutionalMemoryEntry,
    EmbeddingEventType,
    EmbeddingRequest,
    RAGQuery,
    SimilarityResult,
)


class TestInstitutionalMemoryEntry:
    def test_creation(self):
        entry = InstitutionalMemoryEntry(
            event_type=EmbeddingEventType.THESIS_INVALIDATED,
            reference_id="ref-123",
            ticker="AAPL",
            content_text="Test content",
            embedding=[0.1] * 1536,
        )
        assert entry.ticker == "AAPL"
        assert len(entry.embedding) == 1536
        assert entry.embedding_model == "text-embedding-3-small"

    def test_immutable(self):
        entry = InstitutionalMemoryEntry(content_text="test")
        with pytest.raises(AttributeError):
            entry.content_text = "changed"


class TestSimilarityResult:
    def test_creation(self):
        entry = InstitutionalMemoryEntry(content_text="test")
        result = SimilarityResult(entry=entry, similarity_score=0.15)
        assert result.similarity_score == 0.15


class TestEmbeddingRequest:
    def test_creation(self):
        req = EmbeddingRequest(
            text="test text",
            event_type=EmbeddingEventType.NEWS_ARTICLE,
            reference_id="art-1",
            ticker="AAPL",
        )
        assert req.ticker == "AAPL"
        assert req.event_type == EmbeddingEventType.NEWS_ARTICLE


class TestContextRetrieval:
    def _make_service(self, search_results=None):
        from karsa.rag.application.context_retrieval import ContextRetrievalService
        mock_repo = MagicMock()
        mock_repo.similarity_search = MagicMock(return_value=search_results or [])
        mock_embed = AsyncMock(return_value=[0.1] * 1536)
        return ContextRetrievalService(
            repository=mock_repo,
            generate_embedding=mock_embed,
        ), mock_repo, mock_embed

    def test_empty_results_returns_empty(self):
        svc, _, _ = self._make_service([])
        async def run():
            result = await svc.retrieve_context(ticker="AAPL")
            assert result == ""
        asyncio.run(run())

    def test_formats_context(self):
        entry = InstitutionalMemoryEntry(
            event_type=EmbeddingEventType.POST_MORTEM_COMPLETED,
            reference_id="pm-1",
            ticker="AAPL",
            sector="Tech",
            content_text="Post-mortem: lost 2% on bad entry timing",
            metadata={"outcome": "LOSS", "pnl": -2.0},
        )
        result = SimilarityResult(entry=entry, similarity_score=0.1)
        svc, _, _ = self._make_service([result])
        async def run():
            ctx = await svc.retrieve_context(ticker="AAPL")
            assert "INSTITUTIONAL MEMORY" in ctx
            assert "AAPL" in ctx
            assert "LOSS" in ctx
        asyncio.run(run())

    def test_degrades_on_embedding_failure(self):
        svc, _, mock_embed = self._make_service()
        mock_embed.side_effect = Exception("API down")
        async def run():
            result = await svc.retrieve_context(ticker="AAPL")
            assert result == ""
        asyncio.run(run())
