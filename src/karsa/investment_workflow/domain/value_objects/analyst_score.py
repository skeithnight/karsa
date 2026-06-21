"""AnalystScore value object -- Sprint-13. ADR-140."""

from dataclasses import dataclass, field
from typing import Any, Dict

from karsa.investment_workflow.domain.value_objects.enums import AnalystType


@dataclass(frozen=True)
class AnalystScore:
    """Individual analyst output score.

    Each analyst produces a score (0-10) with confidence and metrics.
    """

    analyst_type: str  # AnalystType value
    score: float  # 0.0-10.0
    confidence: float  # 0.0-1.0
    metrics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        valid_types = {e.value for e in AnalystType}
        if self.analyst_type not in valid_types:
            raise ValueError(
                f"analyst_type must be one of {valid_types}, got {self.analyst_type}"
            )
        if not 0.0 <= self.score <= 10.0:
            raise ValueError(
                f"score must be 0.0-10.0, got {self.score}"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be 0.0-1.0, got {self.confidence}"
            )
