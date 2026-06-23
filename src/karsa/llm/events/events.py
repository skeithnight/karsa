"""LLM Pool domain events."""
from dataclasses import dataclass
from karsa.shared.domain.event import DomainEvent


@dataclass
class LLMProviderRegisteredEvent(DomainEvent):
    provider_id: str = ""
    name: str = ""
    base_url: str = ""
    priority: int = 100


@dataclass
class LLMProviderStatusChangedEvent(DomainEvent):
    provider_id: str = ""
    old_status: str = ""
    new_status: str = ""


@dataclass
class LLMModelGroupAddedEvent(DomainEvent):
    group_name: str = ""
    model_name: str = ""
    provider_id: str = ""
    priority: int = 100


@dataclass
class LLMModelGroupRemovedEvent(DomainEvent):
    group_name: str = ""
    model_name: str = ""
    provider_id: str = ""


@dataclass
class LLMRouterSettingsUpdatedEvent(DomainEvent):
    group_name: str = ""
    routing_strategy: str = ""
    num_retries: int = 3
    timeout_seconds: int = 60
