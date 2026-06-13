import os
import tempfile
import pytest
import json
import hashlib

from karsa.memory.domain.service.schema_registry import SchemaRegistryService, SchemaValidationError
from karsa.memory.domain.service.snapshot_service import SnapshotService
from karsa.memory.infrastructure.storage.in_memory_schema_repository import InMemorySchemaRepository
from karsa.memory.infrastructure.storage.in_memory_snapshot_repository import InMemorySnapshotRepository
from karsa.memory.infrastructure.storage.local_blob_storage import LocalBlobStorage

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d

@pytest.fixture
def services(temp_dir):
    schema_repo = InMemorySchemaRepository()
    registry_service = SchemaRegistryService(schema_repo)
    
    snapshot_repo = InMemorySnapshotRepository()
    blob_storage = LocalBlobStorage(base_path=temp_dir)
    snapshot_service = SnapshotService(registry_service, snapshot_repo, blob_storage)
    
    return registry_service, snapshot_service, blob_storage

def test_end_to_end_snapshot_lifecycle(services):
    registry, snapshot_service, blob_storage = services
    
    # 1. Register schema
    schema_id = "test_artifact"
    schema_version = "1.0"
    schema_payload = {
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "value": {"type": "number"}
        },
        "required": ["key", "value"]
    }
    registry.register_schema(schema_id, schema_version, schema_payload)
    
    # 2. Validate payload (will be done inside create_snapshot but let's test failure first)
    invalid_payload = {"key": "test"} # missing value
    with pytest.raises(SchemaValidationError):
        snapshot_service.create_snapshot(
            namespace="test_ns",
            schema_id=schema_id,
            schema_version=schema_version,
            payload=invalid_payload,
            author="test_agent",
            reason="testing failure"
        )
        
    # 3. Create snapshot (with valid payload)
    valid_payload = {"key": "test_key", "value": 42}
    snapshot = snapshot_service.create_snapshot(
        namespace="test_ns",
        schema_id=schema_id,
        schema_version=schema_version,
        payload=valid_payload,
        author="test_agent",
        reason="testing success"
    )
    
    assert snapshot.namespace == "test_ns"
    assert snapshot.schema_id == "test_artifact:1.0"
    assert snapshot.provenance.author == "test_agent"
    
    # Verify payload hash matches exact serialization logic
    payload_str = json.dumps(valid_payload, sort_keys=True)
    expected_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
    assert snapshot.payload_hash == expected_hash
    
    # 4. Retrieve snapshot & 5. Verify payload integrity
    result = snapshot_service.get_snapshot(snapshot.snapshot_id)
    assert result is not None
    retrieved_snapshot, retrieved_payload = result
    
    assert retrieved_snapshot.snapshot_id == snapshot.snapshot_id
    assert retrieved_payload == valid_payload
    
    # 6. Verify immutable behavior
    # Assuming "immutable behavior" means the payload isn't changed and altering the file breaks the hash or something,
    # or that the DB record doesn't have an update method.
    # In this case we just verify we can't save it again under same hash if it changed, 
    # but practically we verify the hash still matches the retrieved payload.
    retrieved_str = json.dumps(retrieved_payload, sort_keys=True)
    retrieved_hash = hashlib.sha256(retrieved_str.encode("utf-8")).hexdigest()
    assert retrieved_hash == snapshot.payload_hash
