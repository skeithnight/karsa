"""ReviewAssessmentRepository — Sprint-10.

Write-once repository for immutable review assessments. ADR-106.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from karsa.review_engine.domain.aggregates.review_assessment import ReviewAssessment


class ReviewAssessmentRepository(ABC):
    """Repository for ReviewAssessment aggregate.

    Write-once. No update or delete methods. ADR-106.
    Canonical status is NOT stored here — use ReviewVersionRegistryRepository.
    """

    @abstractmethod
    def save(self, record: ReviewAssessment) -> bool:
        """Save review assessment. Returns False if duplicate (ON CONFLICT DO NOTHING).

        ADR-107: UNIQUE(evaluation_id, review_type, review_version) prevents duplicates.
        """
        ...

    @abstractmethod
    def get_by_id(self, review_id: str) -> Optional[ReviewAssessment]:
        """Get review assessment by technical identity."""
        ...

    @abstractmethod
    def get_by_evaluation_and_type(
        self, evaluation_id: str, review_type: str
    ) -> Optional[ReviewAssessment]:
        """Get review assessment by business identity."""
        ...

    @abstractmethod
    def get_by_target_urn(self, target_urn: str) -> List[ReviewAssessment]:
        """Get all review assessments for a target."""
        ...

    @abstractmethod
    def list_reviews(self, page: int = 1, size: int = 50) -> List[ReviewAssessment]:
        """List review assessments with pagination."""
        ...
