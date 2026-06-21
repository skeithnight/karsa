"""CapabilityHealthDTO -- Sprint-11. Wave-8.

Read-only contract for capability health data.
Exposes projection data without leaking projection internals.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CapabilityHealthDTO:
    """Public contract for capability health state.

    Maps from CapabilityHealthProjection without exposing
    projection table structure or internal repository types.
    """

    capability_family_id: str
    capability_urn: str
    current_score: float  # 0.0-1.0
    algorithm_version: str

    # 4-factor breakdown
    execution_quality_score: float = 0.0
    attribution_alignment_score: float = 0.0
    review_sentiment_score: float = 0.0
    regime_fitness_score: float = 0.0

    evaluation_count: int = 0
    data_completeness: float = 0.0
    score_trend: str = "UNKNOWN"  # IMPROVING, STABLE, DECLINING, UNKNOWN
    lifecycle_state: str = "ACTIVE"
    last_evaluated_at: Optional[datetime] = None

    # ADR-138
    consecutive_low_scores: int = 0
    consecutive_high_scores: int = 0
