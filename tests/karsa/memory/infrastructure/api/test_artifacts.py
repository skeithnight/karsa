import pytest
import tempfile
from fastapi import FastAPI
from fastapi.testclient import TestClient

from karsa.memory.infrastructure.api.artifacts import router, get_snapshot_service, get_event_bus
from karsa.memory.domain.service.schema_registry import SchemaRegistryService
from karsa.memory.domain.service.snapshot_service import SnapshotService
from karsa.memory.infrastructure.storage.in_memory_schema_repository import InMemorySchemaRepository
from karsa.memory.infrastructure.storage.in_memory_snapshot_repository import InMemorySnapshotRepository
from karsa.memory.infrastructure.storage.local_blob_storage import LocalBlobStorage
from karsa.memory.infrastructure.event.mock_event_bus import MockEventBus

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d

@pytest.fixture
def test_app(temp_dir):
    app = FastAPI()
    app.include_router(router)
    
    # Setup domain
    schema_repo = InMemorySchemaRepository()
    registry_service = SchemaRegistryService(schema_repo)
    snapshot_repo = InMemorySnapshotRepository()
    blob_storage = LocalBlobStorage(base_path=temp_dir)
    snapshot_service = SnapshotService(registry_service, snapshot_repo, blob_storage)
    event_bus = MockEventBus()
    
    # Register a valid schema
    registry_service.register_schema("test_schema", "1.0", {
        "type": "object",
        "properties": {"foo": {"type": "string"}},
        "required": ["foo"]
    })
    
    # Override dependencies
    app.dependency_overrides[get_snapshot_service] = lambda: snapshot_service
    app.dependency_overrides[get_event_bus] = lambda: event_bus
    
    return app, event_bus

@pytest.fixture
def client(test_app):
    app, _ = test_app
    return TestClient(app)

def test_publish_and_get_artifact(client, test_app):
    _, event_bus = test_app
    
    payload = {
        "namespace": "my_domain",
        "schema_id": "test_schema",
        "schema_version": "1.0",
        "author": "tester",
        "reason": "testing api",
        "payload": {"foo": "bar"}
    }
    
    # Publish artifact
    response = client.post("/artifacts", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "snapshot_id" in data
    assert data["namespace"] == "my_domain"
    assert data["schema_id"] == "test_schema:1.0"
    
    # Verify event published
    assert len(event_bus.published_events) == 1
    event = event_bus.published_events[0]
    assert event.snapshot_id == data["snapshot_id"]
    
    # Retrieve artifact
    snapshot_id = data["snapshot_id"]
    get_res = client.get(f"/artifacts/{snapshot_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["snapshot_id"] == snapshot_id
    assert get_data["payload"] == {"foo": "bar"}

def test_publish_invalid_schema(client):
    payload = {
        "namespace": "my_domain",
        "schema_id": "test_schema",
        "schema_version": "1.0",
        "author": "tester",
        "reason": "testing invalid schema",
        "payload": {"baz": 123} # Missing 'foo'
    }
    
    response = client.post("/artifacts", json=payload)
    assert response.status_code == 400
    assert "Payload validation failed" in response.json()["detail"]

def test_get_missing_artifact(client):
    response = client.get("/artifacts/does_not_exist")
    assert response.status_code == 404
