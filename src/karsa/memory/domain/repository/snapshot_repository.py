from abc import ABC, abstractmethod
from typing import Optional, List
from karsa.memory.domain.model.snapshots import ImmutableSnapshot, ArtifactLineage, ArtifactSchema

class SnapshotRepository(ABC):
    @abstractmethod
    def save_snapshot(self, snapshot: ImmutableSnapshot) -> None:
        pass
        
    @abstractmethod
    def get_snapshot(self, snapshot_id: str) -> Optional[ImmutableSnapshot]:
        pass

    @abstractmethod
    def save_lineage(self, lineage: ArtifactLineage) -> None:
        pass

class SchemaRepository(ABC):
    @abstractmethod
    def save_schema(self, schema: ArtifactSchema) -> None:
        pass
        
    @abstractmethod
    def get_schema(self, schema_id: str, version: str) -> Optional[ArtifactSchema]:
        pass
