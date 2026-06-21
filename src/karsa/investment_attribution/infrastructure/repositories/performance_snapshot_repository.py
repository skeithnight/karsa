"""PerformanceSnapshotRepository ABC -- Sprint-18."""

from abc import ABC, abstractmethod
from typing import List, Optional


class PerformanceSnapshotRepository(ABC):
    """Repository for daily performance snapshots."""

    @abstractmethod
    def save(self, snapshot) -> bool:
        """Persist a snapshot. Returns False on duplicate date."""

    @abstractmethod
    def get_by_date(self, snapshot_date: str):
        """Lookup by date string."""

    @abstractmethod
    def get_latest(self):
        """Get the most recent snapshot."""

    @abstractmethod
    def list_snapshots(self, limit: int = 30) -> List:
        """Recent snapshots, newest first."""
