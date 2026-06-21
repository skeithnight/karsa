"""ResearchDocumentRepository ABC -- Sprint-14."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ResearchDocumentRepository(ABC):
    """Write-once repository for research documents."""

    @abstractmethod
    def save(self, record: Any) -> bool:
        """Persist a document. Returns False on duplicate."""

    @abstractmethod
    def get_by_id(self, document_id: str) -> Optional[Any]:
        """Lookup by document_id URN."""

    @abstractmethod
    def search_by_ticker(self, ticker: str) -> List[Any]:
        """Find documents related to a ticker."""

    @abstractmethod
    def search_by_sector(self, sector: str) -> List[Any]:
        """Find documents related to a sector."""

    @abstractmethod
    def search_by_type(self, doc_type: str) -> List[Any]:
        """Find documents by type."""

    @abstractmethod
    def list_documents(self, page: int = 1, size: int = 50) -> List[Any]:
        """Paginated listing of all documents."""

    @abstractmethod
    def search_by_embedding(
        self, query_embedding: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Vector similarity search. Returns documents with scores."""
