"""Tests for KnowledgeService -- Sprint-14.

Covers:
- load document
- query by ticker
- query by sector
- query by type
- duplicate detection
- get document
"""

import pytest

from karsa.investment_knowledge.application.knowledge_service import (
    KnowledgeService,
    LoadDocumentCommand,
    QueryCommand,
)
from karsa.investment_knowledge.domain.value_objects.enums import DocumentType
from karsa.investment_knowledge.infrastructure.persistence.in_memory_research_document_repository import (
    InMemoryResearchDocumentRepository,
)


def _make_service():
    repo = InMemoryResearchDocumentRepository()
    return KnowledgeService(document_repo=repo), repo


def _load_sample(service, title="Banking Sector Analysis", ticker="BBCA"):
    cmd = LoadDocumentCommand(
        title=title,
        content="A" * 200,
        doc_type=DocumentType.SECTOR_ANALYSIS.value,
        ticker=ticker,
        sector="Banking",
    )
    return service.load_document(cmd)


class TestLoadDocument:
    """Load research documents into knowledge base."""

    def test_load_success(self):
        service, repo = _make_service()
        result = _load_sample(service)
        assert result.success is True
        assert result.document_id is not None

    def test_load_saves_to_repo(self):
        service, repo = _make_service()
        result = _load_sample(service)
        doc = repo.get_by_id(result.document_id)
        assert doc is not None
        assert doc.title == "Banking Sector Analysis"

    def test_duplicate_rejected(self):
        service, repo = _make_service()
        r1 = _load_sample(service)
        r2 = _load_sample(service)
        assert r1.success is True
        assert r2.success is False
        assert "already exists" in r2.message

    def test_load_with_metadata(self):
        service, repo = _make_service()
        cmd = LoadDocumentCommand(
            title="ASII Profile",
            content="A" * 200,
            doc_type=DocumentType.COMPANY_PROFILE.value,
            ticker="ASII",
            sector="Automotive",
            metadata={"market_cap": "50T IDR"},
        )
        result = service.load_document(cmd)
        assert result.success is True
        doc = repo.get_by_id(result.document_id)
        assert doc.metadata["market_cap"] == "50T IDR"


class TestQuery:
    """Query the knowledge base."""

    def test_query_by_ticker(self):
        service, repo = _make_service()
        _load_sample(service, "BBCA Analysis", "BBCA")
        _load_sample(service, "ASII Analysis", "ASII")

        cmd = QueryCommand(query="BBCA", ticker_filter="BBCA")
        result = service.query(cmd)
        assert result.count == 1
        assert result.results[0]["ticker"] == "BBCA"

    def test_query_by_sector(self):
        service, repo = _make_service()
        _load_sample(service, "Banking 1", "BBCA")
        _load_sample(service, "Banking 2", "BBRI")

        cmd = QueryCommand(query="banking", sector_filter="Banking")
        result = service.query(cmd)
        assert result.count == 2

    def test_query_by_type(self):
        service, repo = _make_service()
        cmd1 = LoadDocumentCommand(
            title="Sector Analysis",
            content="A" * 200,
            doc_type=DocumentType.SECTOR_ANALYSIS.value,
        )
        cmd2 = LoadDocumentCommand(
            title="Company Profile",
            content="B" * 200,
            doc_type=DocumentType.COMPANY_PROFILE.value,
        )
        service.load_document(cmd1)
        service.load_document(cmd2)

        cmd = QueryCommand(
            query="sector",
            type_filter=DocumentType.SECTOR_ANALYSIS.value,
        )
        result = service.query(cmd)
        assert result.count == 1

    def test_query_empty(self):
        service, _ = _make_service()
        cmd = QueryCommand(query="nothing")
        result = service.query(cmd)
        assert result.count == 0

    def test_query_top_k(self):
        service, _ = _make_service()
        for i in range(10):
            _load_sample(service, f"Doc {i}", f"T{i}")

        cmd = QueryCommand(query="all", top_k=3)
        result = service.query(cmd)
        assert result.count == 3


class TestGetDocument:
    """Get document by ID."""

    def test_get_existing(self):
        service, _ = _make_service()
        result = _load_sample(service)
        doc = service.get_document(result.document_id)
        assert doc is not None
        assert doc.title == "Banking Sector Analysis"

    def test_get_nonexistent(self):
        service, _ = _make_service()
        doc = service.get_document("nonexistent")
        assert doc is None

    def test_list_by_ticker(self):
        service, _ = _make_service()
        _load_sample(service, "BBCA 1", "BBCA")
        _load_sample(service, "BBCA 2", "BBCA")
        _load_sample(service, "ASII 1", "ASII")

        results = service.list_by_ticker("BBCA")
        assert len(results) == 2
