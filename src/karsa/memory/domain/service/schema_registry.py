import jsonschema
from typing import Dict, Any, Optional
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError
from karsa.memory.domain.model.snapshots import ArtifactSchema
from karsa.memory.domain.repository.snapshot_repository import SchemaRepository

class SchemaValidationError(Exception):
    pass

class SchemaRegistryService:
    def __init__(self, repository: SchemaRepository):
        self._repository = repository
        
    def register_schema(self, schema_id: str, version: str, json_schema: Dict[str, Any]) -> ArtifactSchema:
        """Registers a new artifact schema and saves it to the repository."""
        # Validate that the provided schema is a valid JSON Schema
        try:
            jsonschema.Draft202012Validator.check_schema(json_schema)
        except jsonschema.exceptions.SchemaError as e:
            raise SchemaValidationError(f"Invalid JSON schema definition: {str(e)}")
            
        schema = ArtifactSchema(
            schema_id=schema_id,
            version=version,
            json_schema=json_schema,
            active=True
        )
        self._repository.save_schema(schema)
        return schema
        
    def lookup_schema(self, schema_id: str, version: str) -> Optional[ArtifactSchema]:
        """Looks up a specific version of a schema."""
        return self._repository.get_schema(schema_id, version)
        
    def validate_payload(self, schema_id: str, version: str, payload: Dict[str, Any]) -> None:
        """Validates a JSON payload against the requested schema version."""
        schema = self.lookup_schema(schema_id, version)
        if not schema:
            raise SchemaValidationError(f"Schema not found: {schema_id} v{version}")
            
        if not schema.active:
            raise SchemaValidationError(f"Schema {schema_id} v{version} is not active")
            
        try:
            jsonschema.validate(instance=payload, schema=schema.json_schema)
        except JSONSchemaValidationError as e:
            raise SchemaValidationError(f"Payload validation failed: {e.message}")
