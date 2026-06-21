"""CapabilityHealthProjection DTO -- Sprint-11. ADR-131, ADR-132, ADR-136."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from karsa.capability_engine.domain.value_objects.enums import ScoreTrend


@dataclass(frozen=True)
class CapabilityHealthProjection:
    """Read model for capability health scores.

    ADR-131: Every ACTIVE capability must have a row.
    Default score = 0.5, data_completeness = 0.0, score_trend = UNKNOWN.
    """

    capability_family_id: str  # UUID
    capability_urn: str  # URN of current capability version
    current_score: float = 0.5  # 0.0-1.0, default neutral (ADR-131)
    algorithm_version: str = "v1.0"  # ADR-134

    # 4-factor component scores (ADR-132)
    execution_quality_score: float = 0.0
    attribution_alignment_score: float = 0.0
    review_sentiment_score: float = 0.0
    regime_fitness_score: float = 0.0

    evaluation_count: int = 0
    data_completeness: float = 0.0  # ADR-131: default 0.0
    score_trend: str = ScoreTrend.UNKNOWN.value  # ADR-136
    lifecycle_state: str = "ACTIVE"
    last_evaluated_at: Optional[datetime] = None

    # ADR-138: Governance counters
    consecutive_low_scores: int = 0
    consecutive_high_scores: int = 0

    def __post_init__(self) -> None:
        if not self.capability_family_id:
            raise ValueError("capability_family_id is required")
        if not self.capability_urn:
            raise ValueError("capability_urn is required")
        if not 0.0 <= self.current_score <= 1.0:
            raise ValueError(
                f"current_score must be 0.0-1.0, got {self.current_score}"
            )
        if not 0.0 <= self.data_completeness <= 1.0:
            raise ValueError(
                f"data_completeness must be 0.0-1.0, got {self.data_completeness}"
            )
        if self.evaluation_count < 0:
            raise ValueError(
                f"evaluation_count must be >= 0, got {self.evaluation_count}"
            )
        if self.consecutive_low_scores < 0:
            raise ValueError("consecutive_low_scores must be >= 0")
        if self.consecutive_high_scores < 0:
            raise ValueError("consecutive_high_scores must be >= 0")
