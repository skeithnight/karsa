"""CapabilityScoreTimeseriesProjectionRepository ABC -- Sprint-11. ADR-137."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class CapabilityScoreTimeseriesProjectionRepository(ABC):
    """Read-only projection repository for score time series.

    ADR-137: Version boundaries preserved.
    ADR-136: Ordered by evaluation_sequence.
    """

    @abstractmethod
    def get_by_family(
        self, capability_family_id: str
    ) -> List[Dict[str, Any]]:
        """All time series entries for a capability family, ordered by sequence."""

    @abstractmethod
    def get_by_family_and_version(
        self, capability_family_id: str, capability_version_id: str
    ) -> List[Dict[str, Any]]:
        """Time series entries filtered by version (ADR-137)."""

    @abstractmethod
    def rebuild_all(self) -> None:
        """Full projection rebuild from source tables."""
