"""RAG Domain Models — Institutional Memory entries for pgvector.

Immutable entries storing embeddings of theses, post-mortems, and news
for retrieval-augmented generation.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class EmbeddingEventType(str, Enum):
    """Type of event that generated the embedding."""
    THESIS_INVALIDATED = "thesis_invalidated"
    POST_MORTEM_COMPLETED = "post_mortem_completed"
    NEWS_ARTICLE = "news_article"
    THESIS_APPROVED = "thesis_approved"
    THESIS_REJECTED = "thesis_rejected"


@dataclass(frozen=True)
class InstitutionalMemoryEntry:
    """Aggregate: an immutable embedding entry in institutional memory.

    Once written, never updated. Metadata includes outcome (WIN/LOSS),
    PnL, horizon for future retrieval filtering.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EmbeddingEventType = EmbeddingEventType.NEWS_ARTICLE
    reference_id: str = ""
    ticker: Optional[str] = None
    sector: Optional[str] = None
    content_text: str = ""
    embedding: Optional[List[float]] = None  # 1536-dim for text-embedding-3-small
    embedding_model: str = "text-embedding-3-small"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class EmbeddingRequest:
    """Value object: a request to generate and store an embedding."""
    text: str
    event_type: EmbeddingEventType
    reference_id: str
    ticker: Optional[str] = None
    sector: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RAGQuery:
    """Value object: a query for similar institutional memory entries."""
    query_text: str
    ticker: Optional[str] = None
    sector: Optional[str] = None
    top_k: int = 5
    event_types: Optional[List[EmbeddingEventType]] = None


@dataclass(frozen=True)
class SimilarityResult:
    """Value object: a single result from a similarity search."""
    entry: InstitutionalMemoryEntry
    similarity_score: float  # 0.0 (identical) to 2.0 (opposite), cosine distance
