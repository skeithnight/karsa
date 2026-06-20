"""ReviewRecordRepository contract — Sprint-07 Wave-2B."""
from abc import ABC, abstractmethod
from typing import Optional, List

from karsa.review.domain.aggregates.review_record import ReviewRecord


class ReviewRecordRepository(ABC):
    """Repository contract for ReviewRecord aggregate.

    Write-once ledger entry. No update or delete methods.
    """

    @abstractmethod
    def save_record(self, record: ReviewRecord) -> None:
        """Saves a review record to the write-once ledger.

        Raises:
            ImmutabilityViolationException: If review_id already exists.
            ForeignKeyViolation: If cycle_id does not reference a valid ReviewCycle.
        """
        pass

    @abstractmethod
    def get_record_by_id(self, review_id: str) -> Optional[ReviewRecord]:
        """Retrieves a review record by its unique identifier.

        Args:
            review_id: The unique review identifier.

        Returns:
            The ReviewRecord if found, None otherwise.
        """
        pass

    @abstractmethod
    def get_records_by_cycle_id(self, cycle_id: str) -> List[ReviewRecord]:
        """Retrieves all review records for a given review cycle.

        Args:
            cycle_id: The review cycle identifier.

        Returns:
            List of ReviewRecord instances ordered by executed_at.
        """
        pass

    @abstractmethod
    def list_records(self, page: int = 1, size: int = 50) -> List[ReviewRecord]:
        """Lists review records with pagination.

        Args:
            page: Page number (1-indexed).
            size: Page size.

        Returns:
            List of ReviewRecord instances ordered by executed_at DESC.
        """
        pass
