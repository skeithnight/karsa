"""CapabilityScoreAdjustmentRepository contract — Sprint-07 Wave-2B."""
from abc import ABC, abstractmethod
from typing import List

from karsa.review.domain.aggregates.capability_score_adjustment import CapabilityScoreAdjustment


class CapabilityScoreAdjustmentRepository(ABC):
    """Repository contract for CapabilityScoreAdjustment aggregate.

    Write-once ledger entry. Stores only deltas.
    Current score derived from CapabilityScoreProjection via SUM(score_delta).
    """

    @abstractmethod
    def save_adjustment(self, adjustment: CapabilityScoreAdjustment) -> None:
        """Saves a single capability score adjustment to the write-once ledger.

        Raises:
            ImmutabilityViolationException: If adjustment_id already exists.
            ForeignKeyViolation: If review_id does not reference a valid ReviewRecord.
        """
        pass

    @abstractmethod
    def save_adjustments(self, adjustments: List[CapabilityScoreAdjustment]) -> None:
        """Saves multiple capability score adjustments atomically.

        All adjustments are saved or none (transactional batch insert).

        Args:
            adjustments: List of CapabilityScoreAdjustment instances to save.

        Raises:
            ImmutabilityViolationException: If any adjustment_id already exists.
            ForeignKeyViolation: If any review_id does not reference a valid ReviewRecord.
        """
        pass

    @abstractmethod
    def get_adjustments_by_review_id(self, review_id: str) -> List[CapabilityScoreAdjustment]:
        """Retrieves all capability score adjustments for a given review.

        Args:
            review_id: The review identifier.

        Returns:
            List of CapabilityScoreAdjustment instances.
        """
        pass

    @abstractmethod
    def get_adjustments_by_target_urn(self, target_urn: str) -> List[CapabilityScoreAdjustment]:
        """Retrieves all capability score adjustments for a given target across all reviews.

        Args:
            target_urn: The target URN (worker, thesis, strategy).

        Returns:
            List of CapabilityScoreAdjustment instances ordered by created_at.
        """
        pass
