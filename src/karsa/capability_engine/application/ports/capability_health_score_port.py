"""CapabilityHealthScorePort -- Sprint-11. Wave-9R. TD-004.

Port interface for health score aggregate persistence.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional


class CapabilityHealthScorePort(ABC):
    """Mutable port for health score aggregates. ADR-132. OCC via aggregate_version."""

    @abstractmethod
    def save(self, aggregate: Any) -> bool:
        """Upsert with OCC. Returns False on version conflict."""

    @abstractmethod
    def get_by_family_id(
        self, capability_family_id: str
    ) -> Optional[Any]:
        """Load health score by capability family ID."""

    @abstractmethod
    def list_by_score_range(
        self, min_score: float, max_score: float
    ) -> List[Any]:
        """Range query for allocation consumption."""

    @abstractmethod
    def list_all(self, page: int = 1, size: int = 50) -> List[Any]:
        """Paginated listing of all health scores."""
