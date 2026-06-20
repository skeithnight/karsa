from typing import Dict, Any, Optional
from datetime import datetime
import uuid
from karsa.shared.domain.aggregate import AggregateRoot
from karsa.providers.events.events import (
    ProviderRegisteredEvent, ProviderEnabledEvent, ProviderDisabledEvent,
    ProviderHealthChangedEvent, DatalakeBlobStoredEvent
)

class ProviderDefinition(AggregateRoot):
    def __init__(self, provider_id: str, name: str, ptype: str, configuration: Dict[str, Any]):
        super().__init__()
        self.provider_id = provider_id
        self.aggregate_id = provider_id
        self.name = name
        self.type = ptype
        self.enabled = True
        self.configuration = configuration
        self.created_at = datetime.utcnow()
        self.updated_at = self.created_at
        
        self.record_event(ProviderRegisteredEvent(
            provider_id=self.provider_id,
            provider_name=self.name,
            provider_type=self.type
        ))

    def enable(self):
        if not self.enabled:
            self.enabled = True
            self.updated_at = datetime.utcnow()
            self.record_event(ProviderEnabledEvent(provider_id=self.provider_id))

    def disable(self):
        if self.enabled:
            self.enabled = False
            self.updated_at = datetime.utcnow()
            self.record_event(ProviderDisabledEvent(provider_id=self.provider_id))

class ProviderHealth(AggregateRoot):
    def __init__(self, provider_id: str):
        super().__init__()
        self.provider_id = provider_id
        self.aggregate_id = provider_id
        self.status = "UNKNOWN"
        self.latency_ms = 0
        self.last_success_at: Optional[datetime] = None
        self.last_failure_at: Optional[datetime] = None
        self.consecutive_failures = 0

    def record_success(self, latency_ms: int):
        self.last_success_at = datetime.utcnow()
        self.consecutive_failures = 0
        self.latency_ms = latency_ms
        new_status = "HEALTHY"
        if new_status != self.status:
            self.status = new_status
            self.record_event(ProviderHealthChangedEvent(
                provider_id=self.provider_id, status=self.status, latency_ms=self.latency_ms
            ))

    def record_failure(self):
        self.last_failure_at = datetime.utcnow()
        self.consecutive_failures += 1
        new_status = "DEGRADED" if self.consecutive_failures < 3 else "UNAVAILABLE"
        if new_status != self.status:
            self.status = new_status
            self.record_event(ProviderHealthChangedEvent(
                provider_id=self.provider_id, status=self.status, latency_ms=self.latency_ms
            ))

class DatalakeBlob(AggregateRoot):
    def __init__(self, provider_id: str, asset_id: str, payload: Dict[str, Any], extracted_at: datetime, retention_until: Optional[datetime]):
        super().__init__()
        self.blob_id = str(uuid.uuid4())
        self.aggregate_id = self.blob_id
        self.provider_id = provider_id
        self.asset_id = asset_id
        self.payload = payload
        self.extracted_at = extracted_at
        self.retention_until = retention_until
        
        self.record_event(DatalakeBlobStoredEvent(
            blob_id=self.blob_id,
            provider_id=self.provider_id,
            asset_id=self.asset_id,
            extracted_at=self.extracted_at
        ))
