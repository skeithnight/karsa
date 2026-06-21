"""KnowledgeService -- Sprint-14.

Application service for research document management and RAG retrieval.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from karsa.investment_knowledge.domain.aggregates.research_document import (
    ResearchDocument,
)
from karsa.investment_knowledge.domain.exceptions import InvalidDocumentError
from karsa.investment_knowledge.infrastructure.repositories.research_document_repository import (
    ResearchDocumentRepository,
)


@dataclass
class LoadDocumentCommand:
    """Input DTO for loading a document."""

    title: str
    content: str
    doc_type: str
    ticker: Optional[str] = None
    sector: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class QueryCommand:
    """Input DTO for RAG query."""

    query: str
    top_k: int = 5
    ticker_filter: Optional[str] = None
    sector_filter: Optional[str] = None
    type_filter: Optional[str] = None


@dataclass
class QueryResult:
    """Output DTO from RAG query."""

    query: str
    results: List[Dict[str, Any]]
    count: int


@dataclass
class KnowledgeResult:
    """Output DTO from knowledge operations."""

    success: bool
    message: str
    document_id: Optional[str] = None


class KnowledgeService:
    """Application service for knowledge management."""

    def __init__(
        self, document_repo: ResearchDocumentRepository
    ) -> None:
        self._document_repo = document_repo

    def load_document(self, command: LoadDocumentCommand) -> KnowledgeResult:
        """Load a research document into the knowledge base."""
        document_id = f"urn:karsa:knowledge:doc:{uuid.uuid4().hex}"
        content_hash = hashlib.sha256(
            command.content.encode("utf-8")
        ).hexdigest()

        doc = ResearchDocument(
            document_id=document_id,
            title=command.title,
            content=command.content,
            doc_type=command.doc_type,
            ticker=command.ticker,
            sector=command.sector,
            content_hash=content_hash,
            metadata=command.metadata or {},
        )

        saved = self._document_repo.save(doc)
        if not saved:
            return KnowledgeResult(
                success=False,
                message=f"Document with title '{command.title}' already exists",
            )

        return KnowledgeResult(
            success=True,
            message="Document loaded",
            document_id=document_id,
        )

    def query(self, command: QueryCommand) -> QueryResult:
        """Query the knowledge base using filters."""
        results = []

        if command.ticker_filter:
            docs = self._document_repo.search_by_ticker(
                command.ticker_filter
            )
        elif command.sector_filter:
            docs = self._document_repo.search_by_sector(
                command.sector_filter
            )
        elif command.type_filter:
            docs = self._document_repo.search_by_type(
                command.type_filter
            )
        else:
            docs = self._document_repo.list_documents(
                page=1, size=command.top_k
            )

        for doc in docs[: command.top_k]:
            results.append(
                {
                    "document_id": doc.document_id,
                    "title": doc.title,
                    "doc_type": doc.doc_type,
                    "ticker": doc.ticker,
                    "sector": doc.sector,
                    "content_preview": doc.content[:200],
                    "relevance_score": 1.0,  # filter-based, not vector
                }
            )

        return QueryResult(
            query=command.query,
            results=results,
            count=len(results),
        )

    def get_document(
        self, document_id: str
    ) -> Optional[ResearchDocument]:
        """Get a document by ID."""
        return self._document_repo.get_by_id(document_id)

    def list_by_ticker(self, ticker: str) -> List[ResearchDocument]:
        """List all documents for a ticker."""
        return self._document_repo.search_by_ticker(ticker)
