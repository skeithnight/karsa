"""ResearchDocument aggregate -- Sprint-14.

Write-once aggregate for research documents.
Same ImmutableLedgerEntry pattern as investment_workflow.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from karsa.investment_knowledge.domain.exceptions import InvalidDocumentError
from karsa.investment_knowledge.domain.value_objects.enums import (
    DocumentStatus,
    DocumentType,
)


class ImmutableLedgerEntry:
    """Write-once base class."""

    def __setattr__(self, name: str, value: object) -> None:
        if "_initialized" in self.__dict__ and self._initialized:
            raise AttributeError(
                f"Cannot set attribute '{name}' on immutable ledger entry"
            )
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError(
            f"Cannot delete attribute '{name}' on immutable ledger entry"
        )


@dataclass
class ResearchDocument(ImmutableLedgerEntry):
    """Aggregate for research documents in the knowledge base.

    Documents are loaded from docs/investment_context/ and
    external research sources. Each document has a content hash
    for deduplication and an embedding vector for RAG retrieval.
    """

    # Identity
    document_id: str  # URN

    # Content
    title: str
    content: str
    doc_type: str  # DocumentType value
    ticker: Optional[str] = None  # Related stock ticker
    sector: Optional[str] = None  # Related sector

    # Metadata
    status: str = DocumentStatus.ACTIVE.value
    embedding: Optional[List[float]] = None  # Vector embedding
    content_hash: str = ""  # SHA-256 of content for dedup
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        self._initialized = True
        self._validate()

    def _validate(self) -> None:
        if not self.document_id:
            raise InvalidDocumentError("document_id is required")
        if not self.title:
            raise InvalidDocumentError("title is required")
        if not self.content:
            raise InvalidDocumentError("content is required")
        if len(self.content) < 100:
            raise InvalidDocumentError(
                f"content must be at least 100 characters, got {len(self.content)}"
            )
        valid_types = {e.value for e in DocumentType}
        if self.doc_type not in valid_types:
            raise InvalidDocumentError(
                f"doc_type must be one of {valid_types}, got {self.doc_type}"
            )
        valid_statuses = {e.value for e in DocumentStatus}
        if self.status not in valid_statuses:
            raise InvalidDocumentError(
                f"status must be one of {valid_statuses}, got {self.status}"
            )

    @property
    def is_active(self) -> bool:
        return self.status == DocumentStatus.ACTIVE.value

    @property
    def is_searchable(self) -> bool:
        return self.is_active and self.embedding is not None
