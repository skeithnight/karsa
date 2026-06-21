"""Investment Knowledge domain events -- Sprint-14.

All events are frozen dataclasses.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DocumentLoadedEvent:
    """Published when a research document is loaded into the knowledge base."""

    event_id: str
    document_id: str
    title: str
    doc_type: str
    ticker: Optional[str] = None
    sector: Optional[str] = None
    content_hash: str = ""
    loaded_at: str = ""

    event_sequence: int = 0
    event_type: str = "DocumentLoadedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "document_id": self.document_id,
            "title": self.title,
            "doc_type": self.doc_type,
            "ticker": self.ticker,
            "sector": self.sector,
            "content_hash": self.content_hash,
            "loaded_at": self.loaded_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class DocumentArchivedEvent:
    """Published when a research document is archived."""

    event_id: str
    document_id: str
    reason: str = ""
    archived_at: str = ""

    event_sequence: int = 0
    event_type: str = "DocumentArchivedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "document_id": self.document_id,
            "reason": self.reason,
            "archived_at": self.archived_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class DocumentQueriedEvent:
    """Published when a document is retrieved via RAG query."""

    event_id: str
    query: str
    results_count: int = 0
    top_score: float = 0.0
    queried_at: str = ""

    event_sequence: int = 0
    event_type: str = "DocumentQueriedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "query": self.query,
            "results_count": self.results_count,
            "top_score": self.top_score,
            "queried_at": self.queried_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }
