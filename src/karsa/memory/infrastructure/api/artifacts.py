import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from karsa.memory.domain.service.snapshot_service import SnapshotService
from karsa.memory.domain.model.events import EventBus, ArtifactPublishedEvent
from karsa.memory.domain.service.schema_registry import SchemaValidationError

router = APIRouter(prefix="/artifacts", tags=["artifacts"])

class ArtifactPublishRequest(BaseModel):
    namespace: str
    schema_id: str
    schema_version: str
    author: str
    reason: str
    importance_tier: str = "STANDARD"
    payload: Dict[str, Any]

class ArtifactResponse(BaseModel):
    snapshot_id: str
    namespace: str
    payload_hash: str
    schema_id: str
    importance_tier: str
    created_at: str
    author: str
    reason: str

class ArtifactWithPayloadResponse(ArtifactResponse):
    payload: Dict[str, Any]

def get_snapshot_service() -> SnapshotService:
    # In a real app, this would be injected via FastAPI dependencies and an IoC container.
    # For now, it will be overridden in tests.
    raise NotImplementedError("Dependency must be overridden")

def get_event_bus() -> EventBus:
    raise NotImplementedError("Dependency must be overridden")

@router.post("", response_model=ArtifactResponse, status_code=201)
def publish_artifact(
    req: ArtifactPublishRequest,
    service: SnapshotService = Depends(get_snapshot_service),
    event_bus: EventBus = Depends(get_event_bus)
):
    try:
        snapshot = service.create_snapshot(
            namespace=req.namespace,
            schema_id=req.schema_id,
            schema_version=req.schema_version,
            payload=req.payload,
            author=req.author,
            reason=req.reason,
            importance_tier=req.importance_tier
        )
    except SchemaValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    event = ArtifactPublishedEvent(
        event_id=str(uuid.uuid4()),
        snapshot_id=snapshot.snapshot_id,
        namespace=snapshot.namespace,
        schema_id=snapshot.schema_id,
        published_at=datetime.now(timezone.utc)
    )
    event_bus.publish(event)
    
    return ArtifactResponse(
        snapshot_id=snapshot.snapshot_id,
        namespace=snapshot.namespace,
        payload_hash=snapshot.payload_hash,
        schema_id=snapshot.schema_id,
        importance_tier=snapshot.importance_tier,
        created_at=snapshot.created_at.isoformat(),
        author=snapshot.provenance.author,
        reason=snapshot.provenance.reason
    )

@router.get("/{snapshot_id}", response_model=ArtifactWithPayloadResponse)
def get_artifact(
    snapshot_id: str,
    service: SnapshotService = Depends(get_snapshot_service)
):
    result = service.get_snapshot(snapshot_id)
    if not result:
        raise HTTPException(status_code=404, detail="Snapshot not found")
        
    snapshot, payload = result
    
    return ArtifactWithPayloadResponse(
        snapshot_id=snapshot.snapshot_id,
        namespace=snapshot.namespace,
        payload_hash=snapshot.payload_hash,
        schema_id=snapshot.schema_id,
        importance_tier=snapshot.importance_tier,
        created_at=snapshot.created_at.isoformat(),
        author=snapshot.provenance.author,
        reason=snapshot.provenance.reason,
        payload=payload
    )
