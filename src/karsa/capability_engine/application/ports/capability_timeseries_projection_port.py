"""CapabilityTimeseriesProjectionPort -- Sprint-11. Wave-9R. TD-004.

Port interface for score timeseries projection. ADR-137.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class CapabilityTimeseriesProjectionPort(ABC):
    """Read-only port for score time series. ADR-137."""

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
