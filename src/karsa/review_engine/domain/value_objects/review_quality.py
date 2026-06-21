"""ReviewQuality value object — Sprint-10."""
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class ReviewQuality:
    """Quality gate metrics for review."""
    quality_score: float  # 0.0–1.0
    data_completeness: float  # 0.0–1.0
    analysis_depth: float  # 0.0–1.0
    missing_data: List[str] = field(default_factory=list)

    @property
    def is_sufficient(self) -> bool:
        """Quality score >= 0.3 required for completed review."""
        return self.quality_score >= 0.3

    def __post_init__(self):
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError("quality_score must be between 0.0 and 1.0")
        if not 0.0 <= self.data_completeness <= 1.0:
            raise ValueError("data_completeness must be between 0.0 and 1.0")
        if not 0.0 <= self.analysis_depth <= 1.0:
            raise ValueError("analysis_depth must be between 0.0 and 1.0")
