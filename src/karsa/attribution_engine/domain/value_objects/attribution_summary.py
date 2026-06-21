"""AttributionSummary value object — Sprint-09."""
from dataclasses import dataclass, field
from typing import List

from karsa.attribution_engine.domain.value_objects.interaction_effect import InteractionEffect


@dataclass(frozen=True)
class AttributionSummary:
    """Contributing-factor decomposition summary. ADR-095."""
    total_variance_bps: float
    thesis_contribution_bps: float
    execution_contribution_bps: float
    allocation_contribution_bps: float
    regime_contribution_bps: float
    residual_bps: float
    interaction_effects_bps: float
    attribution_confidence: float  # 0.0–1.0
    explanation: str
    interaction_effects: List[InteractionEffect] = field(default_factory=list)

    def validate(self) -> None:
        computed = (
            self.thesis_contribution_bps
            + self.execution_contribution_bps
            + self.allocation_contribution_bps
            + self.regime_contribution_bps
            + self.residual_bps
        )
        assert abs(computed - self.total_variance_bps) < 0.01, (
            f"contributions + residual ({computed}) must equal total_variance ({self.total_variance_bps})"
        )
        assert 0.0 <= self.attribution_confidence <= 1.0
