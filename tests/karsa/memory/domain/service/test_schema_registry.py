import pytest
from karsa.memory.domain.service.schema_registry import SchemaRegistryService, SchemaValidationError
from karsa.memory.infrastructure.storage.in_memory_schema_repository import InMemorySchemaRepository

@pytest.fixture
def repository():
    return InMemorySchemaRepository()

@pytest.fixture
def registry(repository):
    return SchemaRegistryService(repository)

def test_register_and_lookup_schema(registry):
    valid_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "number"}
        },
        "required": ["name"]
    }
    
    schema = registry.register_schema("person", "1.0", valid_schema)
    assert schema.schema_id == "person"
    assert schema.version == "1.0"
    
    lookup = registry.lookup_schema("person", "1.0")
    assert lookup is not None
    assert lookup.schema_id == "person"
    assert lookup.active is True

def test_register_invalid_json_schema(registry):
    invalid_schema = {
        "type": "not_a_valid_type"
    }
    with pytest.raises(SchemaValidationError) as exc:
        registry.register_schema("bad", "1.0", invalid_schema)
    assert "Invalid JSON schema definition" in str(exc.value)

def test_validate_valid_payload(registry):
    valid_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"}
        },
        "required": ["name"]
    }
    registry.register_schema("person", "1.0", valid_schema)
    
    # Should not raise exception
    registry.validate_payload("person", "1.0", {"name": "Alice"})

def test_validate_invalid_payload(registry):
    valid_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"}
        },
        "required": ["name"]
    }
    registry.register_schema("person", "1.0", valid_schema)
    
    with pytest.raises(SchemaValidationError) as exc:
        registry.validate_payload("person", "1.0", {"age": 30})
    assert "Payload validation failed" in str(exc.value)

def test_validate_missing_schema(registry):
    with pytest.raises(SchemaValidationError) as exc:
        registry.validate_payload("missing", "1.0", {"name": "Alice"})
    assert "Schema not found" in str(exc.value)
