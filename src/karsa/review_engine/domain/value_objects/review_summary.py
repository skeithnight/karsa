"""ReviewSummary value object — Sprint-10."""
from dataclasses import dataclass, field
from typing import List

from karsa.review_engine.domain.value_objects.enums import FindingSeverity


@dataclass(frozen=True)
class ReviewSummary:
    """Summary of review findings."""
    total_findings: int
    findings_by_severity: Dict[str, int]  # severity -> count
    total_recommendations: int
    recommendations_by_priority: Dict[str, int]  # priority -> count
    overall_assessment: str  # POSITIVE | NEUTRAL | NEGATIVE
    confidence: float  # 0.0–1.0
    explanation: str

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.overall_assessment not in ("POSITIVE", "NEUTRAL", "NEGATIVE"):
            raise ValueError("overall_assessment must be POSITIVE, NEUTRAL, or NEGATIVE")
