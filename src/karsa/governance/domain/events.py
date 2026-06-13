from dataclasses import dataclass, field
from datetime import datetime
from karsa.domain.events import DomainEvent

@dataclass
class PolicyCreatedEvent(DomainEvent):
    policy_id: str = ""
    policy_urn_str: str = ""
    target_type: str = ""
    target_urn: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class PolicyActivatedEvent(DomainEvent):
    policy_id: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class PolicySuspendedEvent(DomainEvent):
    policy_id: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class PolicyRevokedEvent(DomainEvent):
    policy_id: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class GovernanceDecisionCreatedEvent(DomainEvent):
    decision_id: str = ""
    execution_id: str = ""
    outcome: str = ""  # APPROVED, DENIED
    reason: str = ""
    estimated_cost: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class CapabilityExecutionDeniedEvent(DomainEvent):
    execution_id: str = ""
    capability_urn: str = ""
    decision_id: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class CapabilityExecutionApprovedEvent(DomainEvent):
    execution_id: str = ""
    capability_urn: str = ""
    decision_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class ProviderExecutionDeniedEvent(DomainEvent):
    execution_id: str = ""
    provider_urn: str = ""
    decision_id: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class ProviderExecutionApprovedEvent(DomainEvent):
    execution_id: str = ""
    provider_urn: str = ""
    decision_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class SuspensionRequestedEvent(DomainEvent):
    target_id: str = ""
    target_type: str = ""  # "PROVIDER" or "CAPABILITY"
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class RevocationRequestedEvent(DomainEvent):
    target_id: str = ""
    target_type: str = ""  # "PROVIDER" or "CAPABILITY"
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0

@dataclass
class BudgetConsumptionUpdatedEvent(DomainEvent):
    workflow_id: str = ""
    remaining_budget: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0
