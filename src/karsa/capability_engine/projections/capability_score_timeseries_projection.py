"""CapabilityScoreTimeseriesProjection DTO -- Sprint-11. ADR-137."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CapabilityScoreTimeseriesProjection:
    """Read model for capability score time series.

    Rebuilt from capability_score_history.
    ADR-137: Version boundaries preserved via capability_version_id.
    ADR-136: Ordered by evaluation_sequence.
    """

    capability_family_id: str  # UUID
    capability_version_id: str  # UUID, ADR-137
    evaluation_id: str  # UUID
    evaluation_sequence: int  # ADR-136: monotonic
    score: float  # 0.0-1.0
    algorithm_version: str  # ADR-134
    recorded_at: datetime

    def __post_init__(self) -> None:
        if not self.capability_family_id:
            raise ValueError("capability_family_id is required")
        if not self.capability_version_id:
            raise ValueError("capability_version_id is required")
        if not self.evaluation_id:
            raise ValueError("evaluation_id is required")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(
                f"score must be 0.0-1.0, got {self.score}"
            )
        if self.evaluation_sequence < 0:
            raise ValueError(
                f"evaluation_sequence must be >= 0, got {self.evaluation_sequence}"
            )
        if not self.algorithm_version:
            raise ValueError("algorithm_version is required")
