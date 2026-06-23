"""LLM Pool domain models — DB-driven configuration.

Per-domain config tables following DDD boundaries.
Each LLM provider owns its credentials; model groups reference providers.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List
import uuid

from karsa.shared.domain.aggregate import AggregateRoot
from karsa.llm.events.events import (
    LLMProviderRegisteredEvent,
    LLMProviderStatusChangedEvent,
    LLMModelGroupAddedEvent,
    LLMModelGroupRemovedEvent,
    LLMRouterSettingsUpdatedEvent,
)


class LLMProviderStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"


class RoutingStrategy(str, Enum):
    LATENCY = "latency-based-routing"
    ROUND_ROBIN = "round-robin"
    PRIORITY = "priority-based"


@dataclass
class LLMCredential:
    """Value object wrapping encrypted LLM API key material."""
    ciphertext: str
    nonce: str
    key_rotation_version: int = 1
    expires_at: Optional[datetime] = None


@dataclass
class LLMModelGroupEntry:
    """Value object for a single model within a group."""
    model_name: str
    provider_id: str
    priority: int = 100
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    is_active: bool = True


class LLMProvider(AggregateRoot):
    """Aggregate root for an LLM provider (OpenAI, Anthropic, etc.)."""

    def __init__(
        self,
        provider_id: str,
        name: str,
        base_url: Optional[str] = None,
        priority: int = 100,
    ):
        super().__init__()
        self.provider_id = provider_id
        self.aggregate_id = provider_id
        self.name = name
        self.base_url = base_url
        self.status = LLMProviderStatus.ACTIVE
        self.priority = priority
        self.created_at = datetime.now(timezone.utc)

        self.record_event(LLMProviderRegisteredEvent(
            provider_id=self.provider_id,
            name=self.name,
            base_url=self.base_url or "",
            priority=self.priority,
        ))

    def change_status(self, new_status: LLMProviderStatus) -> None:
        old_status = self.status
        if old_status == new_status:
            return
        self.status = new_status
        self.record_event(LLMProviderStatusChangedEvent(
            provider_id=self.provider_id,
            old_status=old_status.value,
            new_status=new_status.value,
        ))

    def pause(self) -> None:
        self.change_status(LLMProviderStatus.PAUSED)

    def resume(self) -> None:
        self.change_status(LLMProviderStatus.ACTIVE)


@dataclass
class LLMRouterSettings:
    """Router configuration for a model group."""
    group_name: str
    routing_strategy: str = RoutingStrategy.LATENCY.value
    num_retries: int = 3
    timeout_seconds: int = 60
    allowed_fails: int = 2
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
