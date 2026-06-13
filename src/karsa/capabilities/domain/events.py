from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from karsa.domain.events import DomainEvent

@dataclass
class CapabilityRegisteredEvent(DomainEvent):
    capability_id: str = ""
    capability_family_id: str = ""
    urn_str: str = ""
    owner_id: str = ""
    owner_type: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    contract_fingerprint: str = ""
    sequence_number: int = 0

@dataclass
class CapabilityActivatedEvent(DomainEvent):
    capability_id: str = ""
    capability_family_id: str = ""
    urn_str: str = ""
    reason: str = ""
    sequence_number: int = 0

@dataclass
class CapabilityDeprecatedEvent(DomainEvent):
    capability_id: str = ""
    capability_family_id: str = ""
    urn_str: str = ""
    reason: str = ""
    sequence_number: int = 0

@dataclass
class CapabilitySuspendedEvent(DomainEvent):
    capability_id: str = ""
    capability_family_id: str = ""
    urn_str: str = ""
    reason: str = ""
    sequence_number: int = 0

@dataclass
class CapabilityRevokedEvent(DomainEvent):
    capability_id: str = ""
    capability_family_id: str = ""
    urn_str: str = ""
    reason: str = ""
    sequence_number: int = 0

@dataclass
class DependencyValidatedEvent(DomainEvent):
    capability_id: str = ""
    capability_family_id: str = ""
    urn_str: str = ""
    validated_dependencies: List[str] = field(default_factory=list)
    sequence_number: int = 0

@dataclass
class CapabilityLifecycleTransitionedEvent(DomainEvent):
    capability_id: str = ""
    urn_str: str = ""
    previous_state: str = ""
    new_state: str = ""
    transition_reason: str = ""
    sequence_number: int = 0

@dataclass
class CapabilityExecutionStartedEvent(DomainEvent):
    execution_id: str = ""
    capability_urn_str: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    workspace_id: str = ""
    branch_id: str = ""
    input_payload: Dict[str, Any] = field(default_factory=dict)
    sequence_number: int = 0

@dataclass
class CapabilityExecutionCompletedEvent(DomainEvent):
    execution_id: str = ""
    output_payload: Dict[str, Any] = field(default_factory=dict)
    telemetry: Dict[str, Any] = field(default_factory=dict)
    sequence_number: int = 0

@dataclass
class CapabilityExecutionFailedEvent(DomainEvent):
    execution_id: str = ""
    failure_reason: str = ""
    error_message: str = ""
    sequence_number: int = 0
