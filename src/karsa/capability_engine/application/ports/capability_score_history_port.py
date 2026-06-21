"""CapabilityScoreHistoryPort -- Sprint-11. Wave-9R. TD-004.

Port interface for score history persistence. ADR-132, ADR-136.
"""

from abc import ABC, abstractmethod
from typing import Any, List


class CapabilityScoreHistoryPort(ABC):
    """Append-only port for score history. ADR-136: evaluation_sequence ordering."""

    @abstractmethod
    def append(self, entry: Any) -> bool:
        """Append a history entry. Returns False on duplicate sequence."""

    @abstractmethod
    def get_by_family(
        self, capability_family_id: str
    ) -> List[Any]:
        """All history entries for a capability family, ordered by sequence."""

    @abstractmethod
    def get_last_sequence(self, capability_family_id: str) -> int:
        """Return the last recorded evaluation_sequence for a family."""

    @abstractmethod
    def get_by_family_and_version(
        self, capability_family_id: str, capability_version_id: str
    ) -> List[Any]:
        """History entries filtered by version (ADR-137)."""
