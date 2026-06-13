from typing import Optional, Dict
from karsa.memory.domain.model.snapshots import ImmutableSnapshot, ArtifactLineage
from karsa.memory.domain.repository.snapshot_repository import SnapshotRepository

class InMemorySnapshotRepository(SnapshotRepository):
    def __init__(self):
        self._snapshots: Dict[str, ImmutableSnapshot] = {}
        self._lineage: list[ArtifactLineage] = []
        
    def save_snapshot(self, snapshot: ImmutableSnapshot) -> None:
        self._snapshots[snapshot.snapshot_id] = snapshot
        
    def get_snapshot(self, snapshot_id: str) -> Optional[ImmutableSnapshot]:
        return self._snapshots.get(snapshot_id)

    def save_lineage(self, lineage: ArtifactLineage) -> None:
        self._lineage.append(lineage)
