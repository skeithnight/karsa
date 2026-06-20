from typing import Dict, Any, Optional
from datetime import datetime
import hashlib
import json
import uuid
from karsa.shared.domain.aggregate import AggregateRoot
from karsa.evidence.events.events import EvidencePromotedEvent

class PromotedEvidence(AggregateRoot):
    def __init__(self, source_blob_id: str, provider_id: str, asset_id: str, extracted_at: datetime, payload: Dict[str, Any]):
        super().__init__()
        
        self.source_blob_id = source_blob_id
        self.provider_id = provider_id
        self.asset_id = asset_id
        self.extracted_at = extracted_at
        self.payload = payload
        self.promoted_at = datetime.utcnow()
        
        # Calculate content-addressable hash
        payload_str = json.dumps(self.payload, sort_keys=True)
        self.payload_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
        
        # Deterministic Identity via UUIDv5 of payload_hash
        self.evidence_id = str(uuid.uuid5(uuid.NAMESPACE_OID, self.payload_hash))
        self.aggregate_id = self.evidence_id
        
        self.record_event(EvidencePromotedEvent(
            evidence_id=self.evidence_id,
            source_blob_id=self.source_blob_id,
            provider_id=self.provider_id,
            asset_id=self.asset_id,
            payload_hash=self.payload_hash,
            extracted_at=self.extracted_at,
            promoted_at=self.promoted_at
        ))
