"""RecommendationImpact value object — Sprint-10."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RecommendationImpact:
    """Expected impact of implementing a recommendation."""
    expected_return_bps: float
    expected_risk_reduction_pct: float
    implementation_cost_bps: float
    confidence: float  # 0.0–1.0

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
