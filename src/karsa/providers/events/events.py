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


# --- Sprint-51: Data Bridge events ---

@dataclass
class DataBridgeProviderRegisteredEvent(DomainEvent):
    """New provider added to the Data Bridge registry."""
    provider_id: str = ""
    name: str = ""
    ptype: str = ""
    priority: int = 100

@dataclass
class DataBridgeProviderStatusChangedEvent(DomainEvent):
    """Provider status transition (active <-> paused <-> maintenance)."""
    provider_id: str = ""
    old_status: str = ""
    new_status: str = ""

@dataclass
class DataBridgeProviderConfigChangedEvent(DomainEvent):
    """Provider configuration updated — triggers hot-reload."""
    provider_id: str = ""
    config_key: str = ""

@dataclass
class DataBridgeProviderHealthChangedEvent(DomainEvent):
    """Provider health state transition logged."""
    provider_id: str = ""
    status: str = ""
    latency_ms: int = 0
    error_message: str = ""


# --- Sprint-53: Resilience & Failover events ---

@dataclass
class ProviderFailoverEvent(DomainEvent):
    """Traffic switched from primary to fallback provider."""
    source_provider_id: str = ""
    target_provider_id: str = ""
    reason: str = ""
    source_provider_name: str = ""
    target_provider_name: str = ""

@dataclass
class GapFillCompletedEvent(DomainEvent):
    """Missing bars backfilled via REST API recovery."""
    provider_id: str = ""
    symbol: str = ""
    timeframe: str = ""
    bars_filled: int = 0
    gap_start: str = ""
    gap_end: str = ""
