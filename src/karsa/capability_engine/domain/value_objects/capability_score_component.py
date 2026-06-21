"""Capability score component value object -- Sprint-11. ADR-132."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityScoreComponent:
    """Individual dimension score within the composite health score.

    Four components: execution_quality, attribution_alignment,
    review_sentiment, regime_fitness. Weights are policy-configurable
    and sum to 1.0 across all components.
    """

    component_name: str  # ScoreComponentName enum value
    component_score: float  # 0.0-1.0
    weight: float  # 0.0-1.0, sum of all component weights = 1.0
    evaluation_count: int  # number of evaluations contributing
    confidence: float  # 0.0-1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.component_score <= 1.0:
            raise ValueError(
                f"component_score must be 0.0-1.0, got {self.component_score}"
            )
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(
                f"weight must be 0.0-1.0, got {self.weight}"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be 0.0-1.0, got {self.confidence}"
            )
        if self.evaluation_count < 0:
            raise ValueError(
                f"evaluation_count must be >= 0, got {self.evaluation_count}"
            )
        if not self.component_name:
            raise ValueError("component_name is required")
