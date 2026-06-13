import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional

from karsa.memory.domain.model.snapshots import ImmutableSnapshot, ArtifactProvenance
from karsa.memory.domain.repository.snapshot_repository import SnapshotRepository
from karsa.memory.domain.repository.blob_storage import BlobStorage
from karsa.memory.domain.service.schema_registry import SchemaRegistryService

class SnapshotService:
    def __init__(
        self, 
        registry_service: SchemaRegistryService,
        snapshot_repo: SnapshotRepository,
        blob_storage: BlobStorage
    ):
        self._registry_service = registry_service
        self._snapshot_repo = snapshot_repo
        self._blob_storage = blob_storage

    def create_snapshot(
        self, 
        namespace: str,
        schema_id: str,
        schema_version: str,
        payload: Dict[str, Any],
        author: str,
        reason: str,
        importance_tier: str = "STANDARD"
    ) -> ImmutableSnapshot:
        """Validates payload, creates immutable snapshot metadata, and stores blob payload."""
        
        # 1. Validate payload against schema
        self._registry_service.validate_payload(schema_id, schema_version, payload)
        
        # 2. Hash payload (deterministic serialization)
        payload_str = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        
        # 3. Store payload in Blob Storage
        self._blob_storage.store_blob(namespace, payload_hash, payload)
        
        # 4. Create and persist ImmutableSnapshot
        snapshot = ImmutableSnapshot(
            snapshot_id=str(uuid.uuid4()),
            namespace=namespace,
            payload_hash=payload_hash,
            schema_id=f"{schema_id}:{schema_version}",
            importance_tier=importance_tier,
            created_at=datetime.now(timezone.utc),
            provenance=ArtifactProvenance(author=author, reason=reason)
        )
        self._snapshot_repo.save_snapshot(snapshot)
        
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[Tuple[ImmutableSnapshot, Dict[str, Any]]]:
        """Retrieves snapshot metadata and reconstructs it with its payload."""
        snapshot = self._snapshot_repo.get_snapshot(snapshot_id)
        if not snapshot:
            return None
            
        payload = self._blob_storage.retrieve_by_hash(snapshot.namespace, snapshot.payload_hash)
        if not payload:
            return None
            
        return (snapshot, payload)
