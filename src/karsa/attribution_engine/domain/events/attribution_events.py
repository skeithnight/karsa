"""Attribution Engine domain events — Sprint-09."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AttributionDecompositionCompletedEvent:
    """Produced when attribution quality >= 0.3. ADR-099."""
    event_id: str
    attribution_id: str
    evaluation_id: str
    algorithm_version: str
    decision_id: str
    evaluation_horizon_days: int
    target_urn: str
    attribution_summary: Dict[str, Any]
    attribution_quality: Dict[str, Any]
    quality_provenance: Dict[str, Any]  # ADR-105
    regime_context: Dict[str, Any]
    attributed_at: str
    event_sequence: int = 0
    event_type: str = "AttributionDecompositionCompletedEvent"
    event_version: int = 1
    schema_version: int = 1


@dataclass(frozen=True)
class AttributionDecompositionDeferredEvent:
    """Produced when attribution quality < 0.3. ADR-099."""
    event_id: str
    evaluation_id: str
    decision_id: str
    reason: str
    quality_score: float
    missing_data: List[str]
    deferred_at: str
    event_sequence: int = 0
    event_type: str = "AttributionDecompositionDeferredEvent"
    event_version: int = 1
    schema_version: int = 1


@dataclass(frozen=True)
class AttributionCanonicalVersionChangedEvent:
    """Produced when canonical attribution version changes. ADR-102."""
    event_id: str
    evaluation_id: str
    evaluation_horizon_days: int
    target_urn: str
    previous_algorithm_version: Optional[str]
    new_algorithm_version: str
    previous_attribution_id: Optional[str]
    new_attribution_id: str
    changed_at: str
    changed_by: str
    reason: str
    event_sequence: int = 0
    event_type: str = "AttributionCanonicalVersionChangedEvent"
    event_version: int = 1
    schema_version: int = 1
