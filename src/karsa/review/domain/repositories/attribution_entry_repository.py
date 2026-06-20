"""AttributionEntryRepository contract — Sprint-07 Wave-2B."""
from abc import ABC, abstractmethod
from typing import List

from karsa.review.domain.aggregates.attribution_entry import AttributionEntry
from karsa.review.domain.value_objects.review_verdict import AttributionDimension


class AttributionEntryRepository(ABC):
    """Repository contract for AttributionEntry aggregate.

    Write-once ledger entry. Variable cardinality per review per dimension.
    """

    @abstractmethod
    def save_entry(self, entry: AttributionEntry) -> None:
        """Saves a single attribution entry to the write-once ledger.

        Raises:
            ImmutabilityViolationException: If attribution_id already exists.
            ForeignKeyViolation: If review_id does not reference a valid ReviewRecord.
        """
        pass

    @abstractmethod
    def save_entries(self, entries: List[AttributionEntry]) -> None:
        """Saves multiple attribution entries atomically.

        All entries are saved or none (transactional batch insert).

        Args:
            entries: List of AttributionEntry instances to save.

        Raises:
            ImmutabilityViolationException: If any attribution_id already exists.
            ForeignKeyViolation: If any review_id does not reference a valid ReviewRecord.
        """
        pass

    @abstractmethod
    def get_entries_by_review_id(self, review_id: str) -> List[AttributionEntry]:
        """Retrieves all attribution entries for a given review.

        Args:
            review_id: The review identifier.

        Returns:
            List of AttributionEntry instances.
        """
        pass

    @abstractmethod
    def get_entries_by_target_urn(self, target_urn: str) -> List[AttributionEntry]:
        """Retrieves all attribution entries for a given target across all reviews.

        Args:
            target_urn: The target URN (worker, strategy, portfolio).

        Returns:
            List of AttributionEntry instances ordered by created_at DESC.
        """
        pass

    @abstractmethod
    def get_entries_by_dimension(
        self, review_id: str, dimension: AttributionDimension
    ) -> List[AttributionEntry]:
        """Retrieves attribution entries for a review filtered by dimension.

        Args:
            review_id: The review identifier.
            dimension: The attribution dimension to filter by.

        Returns:
            List of AttributionEntry instances for the specified dimension.
        """
        pass
