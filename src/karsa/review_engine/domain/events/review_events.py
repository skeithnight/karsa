"""Review Engine domain events — Sprint-10."""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ReviewCompletedEvent:
    """Produced when review quality >= 0.3."""
    event_id: str
    review_id: str
    evaluation_id: str
    review_type: str
    review_version: str
    target_urn: str
    review_summary: Dict[str, Any]
    review_quality: Dict[str, Any]
    finding_count: int
    recommendation_count: int
    reviewed_at: str
    event_sequence: int = 0
    event_type: str = "ReviewCompletedEvent"
    event_version: int = 1
    schema_version: int = 1


@dataclass(frozen=True)
class ReviewDeferredEvent:
    """Produced when review quality < 0.3."""
    event_id: str
    evaluation_id: str
    review_type: str
    reason: str
    quality_score: float
    missing_data: List[str]
    deferred_at: str
    event_sequence: int = 0
    event_type: str = "ReviewDeferredEvent"
    event_version: int = 1
    schema_version: int = 1


@dataclass(frozen=True)
class ReviewCanonicalVersionChangedEvent:
    """Produced when canonical review version changes."""
    event_id: str
    evaluation_id: str
    review_type: str
    previous_review_id: Optional[str]
    new_review_id: str
    changed_at: str
    changed_by: str
    event_sequence: int = 0
    event_type: str = "ReviewCanonicalVersionChangedEvent"
    event_version: int = 1
    schema_version: int = 1


@dataclass(frozen=True)
class ReviewSizeExceededEvent:
    """Produced when review exceeds ADR-111 size limits."""
    event_id: str
    review_id: str
    finding_count: int
    recommendation_count: int
    limit_findings: int
    limit_recommendations: int
    exceeded_at: str
    event_sequence: int = 0
    event_type: str = "ReviewSizeExceededEvent"
    event_version: int = 1
    schema_version: int = 1
