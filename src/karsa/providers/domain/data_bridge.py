"""Data Bridge domain models — extends providers/ bounded context.

Sprint-51: Database-driven provider management with encrypted credentials,
JSONB configuration, and zero-downtime hot-reload.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List
import uuid

from karsa.shared.domain.aggregate import AggregateRoot
from karsa.providers.events.events import (
    DataBridgeProviderRegisteredEvent,
    DataBridgeProviderStatusChangedEvent,
    DataBridgeProviderConfigChangedEvent,
    DataBridgeProviderHealthChangedEvent,
)


class ProviderType(str, Enum):
    MARKET_TICK = "market_tick"
    MARKET_BAR = "market_bar"
    NEWS = "news"
    SENTIMENT = "sentiment"


class ProviderStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"


class HealthStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RATE_LIMITED = "rate_limited"
    AUTH_ERROR = "auth_error"


@dataclass
class EncryptedCredential:
    """Value object wrapping encrypted API key material."""
    ciphertext: str
    nonce: str
    key_rotation_version: int = 1
    expires_at: Optional[datetime] = None


@dataclass
class ProviderConfig:
    """Value object for JSONB config entries."""
    config_key: str
    config_value: Dict[str, Any]


@dataclass
class HealthLogEntry:
    """Immutable record of provider health state transitions."""
    log_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    provider_id: str = ""
    status: HealthStatus = HealthStatus.DISCONNECTED
    error_message: Optional[str] = None
    latency_ms: Optional[int] = None
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DataBridgeProvider(AggregateRoot):
    """Aggregate root for Data Bridge provider management.

    Extends the existing providers/ bounded context with DB-driven
    configuration, encrypted credentials, and hot-reload support.
    """

    def __init__(
        self,
        provider_id: str,
        name: str,
        ptype: ProviderType,
        priority: int = 100,
    ):
        super().__init__()
        self.provider_id = provider_id
        self.aggregate_id = provider_id
        self.name = name
        self.type = ptype
        self.status = ProviderStatus.ACTIVE
        self.priority = priority
        self.created_at = datetime.now(timezone.utc)

        self.record_event(DataBridgeProviderRegisteredEvent(
            provider_id=self.provider_id,
            name=self.name,
            ptype=self.type.value,
            priority=self.priority,
        ))

    def change_status(self, new_status: ProviderStatus) -> None:
        """Transition provider status (active <-> paused <-> maintenance)."""
        old_status = self.status
        if old_status == new_status:
            return
        self.status = new_status
        self.record_event(DataBridgeProviderStatusChangedEvent(
            provider_id=self.provider_id,
            old_status=old_status.value,
            new_status=new_status.value,
        ))

    def pause(self) -> None:
        self.change_status(ProviderStatus.PAUSED)

    def resume(self) -> None:
        self.change_status(ProviderStatus.ACTIVE)

    def set_maintenance(self) -> None:
        self.change_status(ProviderStatus.MAINTENANCE)

    def notify_config_changed(self, config_key: str) -> None:
        """Emit event when configuration changes (triggers hot-reload)."""
        self.record_event(DataBridgeProviderConfigChangedEvent(
            provider_id=self.provider_id,
            config_key=config_key,
        ))

    def notify_health_changed(
        self,
        status: HealthStatus,
        latency_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Emit event on health state transition."""
        self.record_event(DataBridgeProviderHealthChangedEvent(
            provider_id=self.provider_id,
            status=status.value,
            latency_ms=latency_ms or 0,
            error_message=error_message or "",
        ))
