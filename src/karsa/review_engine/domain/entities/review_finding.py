"""ReviewFinding entity — Sprint-10."""
from dataclasses import dataclass

from karsa.review_engine.domain.value_objects.enums import FindingType, FindingSeverity
from karsa.review_engine.domain.value_objects.review_evidence import ReviewEvidence
from karsa.review_engine.domain.exceptions import InvalidFindingError


@dataclass(frozen=True)
class ReviewFinding:
    """Child entity of ReviewAssessment. ADR-106.

    Stored as JSONB within the parent aggregate.
    Not a separate aggregate — no independent lifecycle.
    """
    finding_id: str
    dimension: str  # THESIS | EXECUTION | ALLOCATION | REGIME | PORTFOLIO
    finding_type: FindingType
    severity: FindingSeverity
    description: str
    evidence: ReviewEvidence
    confidence: float  # 0.0–1.0
    created_at: str  # ISO format

    def __post_init__(self):
        self._validate()

    def _validate(self) -> None:
        if not self.finding_id:
            raise InvalidFindingError("finding_id required")
        if not self.dimension:
            raise InvalidFindingError("dimension required")
        if not 0.0 <= self.confidence <= 1.0:
            raise InvalidFindingError("confidence must be between 0.0 and 1.0")
        if not self.description:
            raise InvalidFindingError("description required")
