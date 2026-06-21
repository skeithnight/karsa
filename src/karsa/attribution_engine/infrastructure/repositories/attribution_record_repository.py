"""AttributionRecordRepository — Sprint-09.

Write-once repository for immutable attribution records. ADR-093.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from karsa.attribution_engine.domain.aggregates.attribution_record import AttributionRecord


class AttributionRecordRepository(ABC):
    """Repository for AttributionRecord aggregate.

    Write-once. No update or delete methods. ADR-093.
    Canonical status is NOT stored here — use AttributionVersionRegistryRepository.
    """

    @abstractmethod
    def save(self, record: AttributionRecord) -> bool:
        """Save attribution record. Returns False if duplicate (ON CONFLICT DO NOTHING).

        ADR-094: UNIQUE(evaluation_id, algorithm_version) prevents duplicates.
        """
        ...

    @abstractmethod
    def get_by_id(self, attribution_id: str) -> Optional[AttributionRecord]:
        """Get attribution record by technical identity."""
        ...

    @abstractmethod
    def get_by_evaluation_and_algorithm(
        self, evaluation_id: str, algorithm_version: str
    ) -> Optional[AttributionRecord]:
        """Get attribution record by business identity. ADR-094."""
        ...

    @abstractmethod
    def get_by_target_urn(self, target_urn: str) -> List[AttributionRecord]:
        """Get all attribution records for a target."""
        ...

    @abstractmethod
    def list_attributions(
        self, page: int = 1, size: int = 50
    ) -> List[AttributionRecord]:
        """List attribution records with pagination."""
        ...
