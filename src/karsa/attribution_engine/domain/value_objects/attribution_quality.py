"""AttributionQuality value object — Sprint-09."""
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class AttributionQuality:
    """Quality gate metrics. ADR-099."""
    quality_score: float  # 0.0–1.0
    data_completeness: float  # 0.0–1.0
    decomposition_confidence: float  # 0.0–1.0
    missing_data: List[str] = field(default_factory=list)

    @property
    def is_sufficient(self) -> bool:
        """ADR-099: quality_score >= 0.3 required for completed event."""
        return self.quality_score >= 0.3

    def validate(self) -> None:
        assert 0.0 <= self.quality_score <= 1.0
        assert 0.0 <= self.data_completeness <= 1.0
        assert 0.0 <= self.decomposition_confidence <= 1.0
