"""In-memory PerformanceSnapshotRepository -- Sprint-18."""

from typing import Dict, List, Optional

from karsa.investment_attribution.domain.value_objects.performance_snapshot import (
    PerformanceSnapshot,
)
from karsa.investment_attribution.infrastructure.repositories.performance_snapshot_repository import (
    PerformanceSnapshotRepository,
)


class InMemoryPerformanceSnapshotRepository(PerformanceSnapshotRepository):
    """In-memory repository for testing."""

    def __init__(self) -> None:
        self._store: Dict[str, PerformanceSnapshot] = {}

    def save(self, snapshot: PerformanceSnapshot) -> bool:
        key = str(snapshot.snapshot_date)
        if key in self._store:
            return False
        self._store[key] = snapshot
        return True

    def get_by_date(self, snapshot_date: str) -> Optional[PerformanceSnapshot]:
        return self._store.get(snapshot_date)

    def get_latest(self) -> Optional[PerformanceSnapshot]:
        if not self._store:
            return None
        return max(self._store.values(), key=lambda s: s.snapshot_date)

    def list_snapshots(self, limit: int = 30) -> List[PerformanceSnapshot]:
        items = sorted(
            self._store.values(),
            key=lambda s: s.snapshot_date,
            reverse=True,
        )
        return items[:limit]
