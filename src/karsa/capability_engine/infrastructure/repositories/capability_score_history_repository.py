"""CapabilityScoreHistoryRepository ABC -- Sprint-11. ADR-132, ADR-136."""

from abc import ABC, abstractmethod
from typing import List, Optional

from karsa.capability_engine.domain.value_objects.score_history_entry import (
    ScoreHistoryEntry,
)


class CapabilityScoreHistoryRepository(ABC):
    """Append-only repository for capability score history.

    ADR-132: History stored in separate table, not embedded in aggregate.
    ADR-136: evaluation_sequence ordering enforced.
    """

    @abstractmethod
    def append(self, entry: ScoreHistoryEntry) -> bool:
        """Append a history entry. Returns False on duplicate sequence."""

    @abstractmethod
    def get_by_family(
        self, capability_family_id: str
    ) -> List[ScoreHistoryEntry]:
        """All history entries for a capability family, ordered by sequence."""

    @abstractmethod
    def get_last_sequence(self, capability_family_id: str) -> int:
        """Return the last recorded evaluation_sequence for a family."""

    @abstractmethod
    def get_by_family_and_version(
        self, capability_family_id: str, capability_version_id: str
    ) -> List[ScoreHistoryEntry]:
        """History entries filtered by version (ADR-137)."""
