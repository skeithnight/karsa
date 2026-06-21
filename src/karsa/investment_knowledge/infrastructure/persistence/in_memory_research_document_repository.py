"""In-memory ResearchDocumentRepository -- Sprint-14."""

import math
from typing import Any, Dict, List, Optional

from karsa.investment_knowledge.domain.aggregates.research_document import (
    ResearchDocument,
)
from karsa.investment_knowledge.infrastructure.repositories.research_document_repository import (
    ResearchDocumentRepository,
)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class InMemoryResearchDocumentRepository(ResearchDocumentRepository):
    """In-memory write-once repository for testing."""

    def __init__(self) -> None:
        self._store: Dict[str, ResearchDocument] = {}
        self._title_key: Dict[str, str] = {}

    def save(self, record: ResearchDocument) -> bool:
        if record.title in self._title_key:
            return False
        self._store[record.document_id] = record
        self._title_key[record.title] = record.document_id
        return True

    def get_by_id(self, document_id: str) -> Optional[ResearchDocument]:
        return self._store.get(document_id)

    def search_by_ticker(self, ticker: str) -> List[ResearchDocument]:
        return [
            d
            for d in self._store.values()
            if d.ticker == ticker and d.is_active
        ]

    def search_by_sector(self, sector: str) -> List[ResearchDocument]:
        return [
            d
            for d in self._store.values()
            if d.sector == sector and d.is_active
        ]

    def search_by_type(self, doc_type: str) -> List[ResearchDocument]:
        return [
            d
            for d in self._store.values()
            if d.doc_type == doc_type and d.is_active
        ]

    def list_documents(
        self, page: int = 1, size: int = 50
    ) -> List[ResearchDocument]:
        items = list(self._store.values())
        start = (page - 1) * size
        return items[start : start + size]

    def search_by_embedding(
        self, query_embedding: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Cosine similarity search."""
        results = []
        for doc in self._store.values():
            if not doc.is_searchable:
                continue
            score = _cosine_similarity(query_embedding, doc.embedding)
            results.append({"document": doc, "score": score})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
