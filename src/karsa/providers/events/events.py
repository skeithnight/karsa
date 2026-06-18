from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime
from karsa.shared.domain.event import DomainEvent

@dataclass
class ProviderRegisteredEvent(DomainEvent):
    provider_id: str = ""
    provider_name: str = ""
    provider_type: str = ""

@dataclass
class ProviderEnabledEvent(DomainEvent):
    provider_id: str = ""

@dataclass
class ProviderDisabledEvent(DomainEvent):
    provider_id: str = ""

@dataclass
class ProviderHealthChangedEvent(DomainEvent):
    provider_id: str = ""
    status: str = ""
    latency_ms: int = 0

@dataclass
class DatalakeBlobStoredEvent(DomainEvent):
    blob_id: str = ""
    provider_id: str = ""
    asset_id: str = ""
    extracted_at: Optional[datetime] = None
