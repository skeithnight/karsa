from dataclasses import dataclass, field
from datetime import datetime
from karsa.domain.events import DomainEvent
from karsa.providers.domain.models import ProviderHealthStatus

@dataclass
class ProviderRegisteredEvent(DomainEvent):
    provider_id: str = ""
    provider_urn_str: str = ""
    input_rate: float = 0.0
    output_rate: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class ProviderActivatedEvent(DomainEvent):
    provider_id: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class ProviderDeprecatedEvent(DomainEvent):
    provider_id: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class ProviderRetiredEvent(DomainEvent):
    provider_id: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class ProviderHealthChangedEvent(DomainEvent):
    provider_id: str = ""
    previous_status: str = ""
    new_status: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class ProviderExecutionSucceededEvent(DomainEvent):
    execution_id: str = ""
    workflow_id: str = ""
    provider_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class ProviderExecutionFailedEvent(DomainEvent):
    execution_id: str = ""
    workflow_id: str = ""
    provider_id: str = ""
    error_message: str = ""
    error_type: str = ""
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0
