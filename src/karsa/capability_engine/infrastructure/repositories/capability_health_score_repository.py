"""CapabilityHealthScoreRepository ABC -- Sprint-11. ADR-132."""

from abc import ABC, abstractmethod
from typing import List, Optional

from karsa.capability_engine.domain.aggregates.capability_health_score import (
    CapabilityHealthScore,
)


class CapabilityHealthScoreRepository(ABC):
    """Mutable repository for capability health score aggregates.

    ADR-132: Separate aggregate from evolution records. Supports
    OCC via aggregate_version field.
    """

    @abstractmethod
    def save(self, aggregate: CapabilityHealthScore) -> bool:
        """Upsert with OCC. Returns False on version conflict."""

    @abstractmethod
    def get_by_family_id(
        self, capability_family_id: str
    ) -> Optional[CapabilityHealthScore]:
        """Load health score by capability family ID."""

    @abstractmethod
    def list_by_score_range(
        self, min_score: float, max_score: float
    ) -> List[CapabilityHealthScore]:
        """Range query for allocation consumption."""

    @abstractmethod
    def list_all(self, page: int = 1, size: int = 50) -> List[CapabilityHealthScore]:
        """Paginated listing of all health scores."""
