"""Tests for ResearchDocument aggregate -- Sprint-14.

Covers:
- aggregate creation
- validation
- immutability
- searchability
- repository
"""

import pytest

from karsa.investment_knowledge.domain.aggregates.research_document import (
    ResearchDocument,
)
from karsa.investment_knowledge.domain.exceptions import InvalidDocumentError
from karsa.investment_knowledge.domain.value_objects.enums import (
    DocumentStatus,
    DocumentType,
)
from karsa.investment_knowledge.infrastructure.persistence.in_memory_research_document_repository import (
    InMemoryResearchDocumentRepository,
)


def _make_document(**overrides):
    defaults = dict(
        document_id="urn:karsa:knowledge:doc:test001",
        title="Banking Sector Indonesia 2026",
        content="A" * 200,  # min 100 chars
        doc_type=DocumentType.SECTOR_ANALYSIS.value,
        ticker="BBCA",
        sector="Banking",
    )
    defaults.update(overrides)
    return ResearchDocument(**defaults)


class TestAggregateCreation:
    """ResearchDocument aggregate creation."""

    def test_valid_document(self):
        doc = _make_document()
        assert doc.document_id == "urn:karsa:knowledge:doc:test001"
        assert doc.title == "Banking Sector Indonesia 2026"
        assert doc.doc_type == DocumentType.SECTOR_ANALYSIS.value

    def test_frozen_after_init(self):
        doc = _make_document()
        with pytest.raises(AttributeError):
            doc.title = "Changed"

    def test_missing_document_id(self):
        with pytest.raises(InvalidDocumentError, match="document_id"):
            _make_document(document_id="")

    def test_missing_title(self):
        with pytest.raises(InvalidDocumentError, match="title"):
            _make_document(title="")

    def test_missing_content(self):
        with pytest.raises(InvalidDocumentError, match="content"):
            _make_document(content="")

    def test_content_too_short(self):
        with pytest.raises(InvalidDocumentError, match="100 characters"):
            _make_document(content="Too short")

    def test_invalid_doc_type(self):
        with pytest.raises(InvalidDocumentError, match="doc_type"):
            _make_document(doc_type="INVALID")

    def test_invalid_status(self):
        with pytest.raises(InvalidDocumentError, match="status"):
            _make_document(status="INVALID")

    def test_is_active(self):
        doc = _make_document()
        assert doc.is_active is True

    def test_is_searchable_with_embedding(self):
        doc = _make_document(embedding=[0.1, 0.2, 0.3])
        assert doc.is_searchable is True

    def test_is_not_searchable_without_embedding(self):
        doc = _make_document()
        assert doc.is_searchable is False

    def test_optional_fields(self):
        doc = _make_document(ticker=None, sector=None)
        assert doc.ticker is None
        assert doc.sector is None

    def test_metadata(self):
        doc = _make_document(metadata={"source": "IDX", "year": 2026})
        assert doc.metadata["source"] == "IDX"


class TestRepository:
    """In-memory repository tests."""

    def test_save_and_retrieve(self):
        repo = InMemoryResearchDocumentRepository()
        doc = _make_document()
        assert repo.save(doc) is True

        loaded = repo.get_by_id(doc.document_id)
        assert loaded is not None
        assert loaded.title == doc.title

    def test_duplicate_save_returns_false(self):
        repo = InMemoryResearchDocumentRepository()
        doc = _make_document()
        assert repo.save(doc) is True
        assert repo.save(doc) is False

    def test_search_by_ticker(self):
        repo = InMemoryResearchDocumentRepository()
        repo.save(_make_document(
            document_id="doc-001",
            title="BBCA Analysis",
            ticker="BBCA",
        ))
        repo.save(_make_document(
            document_id="doc-002",
            title="ASII Analysis",
            ticker="ASII",
        ))

        results = repo.search_by_ticker("BBCA")
        assert len(results) == 1
        assert results[0].ticker == "BBCA"

    def test_search_by_sector(self):
        repo = InMemoryResearchDocumentRepository()
        repo.save(_make_document(
            document_id="doc-001",
            title="Banking Sector",
            sector="Banking",
        ))
        repo.save(_make_document(
            document_id="doc-002",
            title="Energy Sector",
            sector="Energy",
            doc_type=DocumentType.SECTOR_ANALYSIS.value,
        ))

        results = repo.search_by_sector("Banking")
        assert len(results) == 1

    def test_search_by_type(self):
        repo = InMemoryResearchDocumentRepository()
        repo.save(_make_document(
            document_id="doc-001",
            title="Sector Analysis",
            doc_type=DocumentType.SECTOR_ANALYSIS.value,
        ))
        repo.save(_make_document(
            document_id="doc-002",
            title="Company Profile",
            doc_type=DocumentType.COMPANY_PROFILE.value,
        ))

        results = repo.search_by_type(DocumentType.SECTOR_ANALYSIS.value)
        assert len(results) == 1

    def test_embedding_search(self):
        repo = InMemoryResearchDocumentRepository()
        repo.save(_make_document(
            document_id="doc-001",
            title="Doc A",
            embedding=[1.0, 0.0, 0.0],
        ))
        repo.save(_make_document(
            document_id="doc-002",
            title="Doc B",
            embedding=[0.0, 1.0, 0.0],
        ))

        # Query similar to Doc A
        results = repo.search_by_embedding([1.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0]["document"].document_id == "doc-001"
        assert results[0]["score"] > results[1]["score"]
