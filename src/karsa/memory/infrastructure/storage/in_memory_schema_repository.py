from typing import Optional, Dict, Tuple
from karsa.memory.domain.model.snapshots import ArtifactSchema
from karsa.memory.domain.repository.snapshot_repository import SchemaRepository

class InMemorySchemaRepository(SchemaRepository):
    def __init__(self):
        # Key: (schema_id, version) -> ArtifactSchema
        self._schemas: Dict[Tuple[str, str], ArtifactSchema] = {}
        
    def save_schema(self, schema: ArtifactSchema) -> None:
        self._schemas[(schema.schema_id, schema.version)] = schema
        
    def get_schema(self, schema_id: str, version: str) -> Optional[ArtifactSchema]:
        return self._schemas.get((schema_id, version))
