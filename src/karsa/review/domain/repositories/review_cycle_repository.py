"""ReviewCycleRepository contract — Sprint-07 Wave-2B."""
from abc import ABC, abstractmethod
from typing import Optional, List

from karsa.review.domain.aggregates.review_cycle import ReviewCycle


class ReviewCycleRepository(ABC):
    """Repository contract for ReviewCycle aggregate.

    Write-once ledger entry. No update or delete methods.
    """

    @abstractmethod
    def save_cycle(self, cycle: ReviewCycle) -> bool:
        """Saves a review cycle to the write-once ledger.

        Returns:
            True if the cycle was inserted (new row created).
            False if a cycle already exists for this decision_id (ON CONFLICT DO NOTHING).

        This return value is critical for preventing phantom outbox events.
        The caller MUST check the return value before creating outbox events.
        """
        pass

    @abstractmethod
    def get_cycle_by_id(self, cycle_id: str) -> Optional[ReviewCycle]:
        """Retrieves a review cycle by its unique identifier.

        Args:
            cycle_id: The unique cycle identifier.

        Returns:
            The ReviewCycle if found, None otherwise.
        """
        pass

    @abstractmethod
    def get_cycle_by_decision_id(self, decision_id: str) -> Optional[ReviewCycle]:
        """Retrieves a review cycle by the CIO decision it references.

        Args:
            decision_id: The CIO decision identifier.

        Returns:
            The ReviewCycle if found, None otherwise.
        """
        pass

    @abstractmethod
    def get_cycle_by_eligibility_ref(self, eligibility_event_ref: str) -> Optional[ReviewCycle]:
        """Retrieves a review cycle by its eligibility event reference.

        Args:
            eligibility_event_ref: The eligibility event identifier.

        Returns:
            The ReviewCycle if found, None otherwise.
        """
        pass

    @abstractmethod
    def list_cycles(self, page: int = 1, size: int = 50) -> List[ReviewCycle]:
        """Lists review cycles with pagination.

        Args:
            page: Page number (1-indexed).
            size: Page size.

        Returns:
            List of ReviewCycle instances.
        """
        pass
