from dataclasses import dataclass, field
from datetime import datetime, timezone
from karsa.domain.events import DomainEvent

@dataclass
class PolicyCreatedEvent(DomainEvent):
    event_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    policy_id: str = ""
    policy_urn_str: str = ""
    scope_type: str = ""
    scope_urn: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_version: int = 1

@dataclass
class PolicyActivatedEvent(DomainEvent):
    event_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    policy_id: str = ""
    policy_urn_str: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_version: int = 1

@dataclass
class PolicyRetiredEvent(DomainEvent):
    event_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    policy_id: str = ""
    policy_urn_str: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_version: int = 1

@dataclass
class ExceptionGrantedEvent(DomainEvent):
    event_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    token_hash: str = ""
    token_urn: str = ""
    order_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_version: int = 1

@dataclass
class ExceptionExpiredEvent(DomainEvent):
    event_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    token_hash: str = ""
    token_urn: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_version: int = 1

@dataclass
class ExceptionRevokedEvent(DomainEvent):
    event_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    token_hash: str = ""
    token_urn: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_version: int = 1

@dataclass
class GovernanceDecisionCreatedEvent(DomainEvent):
    decision_id: str = ""
    execution_id: str = ""
    outcome: str = ""
    reason: str = ""
    estimated_cost: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class CapabilityExecutionApprovedEvent(DomainEvent):
    execution_id: str = ""
    capability_urn: str = ""
    decision_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class CapabilityExecutionDeniedEvent(DomainEvent):
    execution_id: str = ""
    capability_urn: str = ""
    decision_id: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
