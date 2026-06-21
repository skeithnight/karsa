"""ReviewRecommendation entity — Sprint-10."""
from dataclasses import dataclass

from karsa.review_engine.domain.value_objects.enums import RecommendationType, RecommendationPriority
from karsa.review_engine.domain.exceptions import InvalidRecommendationError


@dataclass(frozen=True)
class ReviewRecommendation:
    """Child entity of ReviewAssessment. ADR-108.

    Stored as JSONB within the parent aggregate.
    Not a separate aggregate — no independent lifecycle.
    """
    recommendation_id: str
    finding_id: str
    recommendation_type: RecommendationType
    priority: RecommendationPriority
    description: str
    expected_impact: str
    implementation_risk: str
    created_at: str  # ISO format

    def __post_init__(self):
        self._validate()

    def _validate(self) -> None:
        if not self.recommendation_id:
            raise InvalidRecommendationError("recommendation_id required")
        if not self.finding_id:
            raise InvalidRecommendationError("finding_id required")
        if not self.description:
            raise InvalidRecommendationError("description required")
        if not self.expected_impact:
            raise InvalidRecommendationError("expected_impact required")
        if not self.implementation_risk:
            raise InvalidRecommendationError("implementation_risk required")
