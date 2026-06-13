import uuid
import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import jsonschema
from karsa.shared.domain.aggregate import VersionedAggregate

class CapabilityLifecycleState(Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"
    REVOKED = "REVOKED"

class ExecutionStatus(Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass(frozen=True)
class CapabilityURN:
    namespace: str
    name: str
    version: str

    def to_string(self) -> str:
        return f"urn:karsa:capability:{self.namespace}:{self.name}:{self.version}"

    @classmethod
    def from_string(cls, urn_str: str) -> "CapabilityURN":
        if not urn_str.startswith("urn:karsa:capability:"):
            raise ValueError(f"Invalid capability URN prefix: {urn_str}")
        parts = urn_str[len("urn:karsa:capability:"):].split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid capability URN format: {urn_str}. Expected namespace:name:version")
        return cls(namespace=parts[0], name=parts[1], version=parts[2])

@dataclass(frozen=True)
class CapabilityOwner:
    owner_id: str
    owner_type: str  # e.g., 'SYSTEM', 'AGENT', 'PARTNER'

@dataclass(frozen=True)
class ExecutionBudget:
    max_cost_usd: float = 0.0
    max_input_tokens: int = 0
    max_output_tokens: int = 0
    timeout_ms: int = 0

@dataclass(frozen=True)
class ExecutionTelemetry:
    duration_ms: int
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    system_metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ExecutionContract:
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)

    def validate_input(self, payload: Dict[str, Any]) -> None:
        try:
            jsonschema.validate(instance=payload, schema=self.input_schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Input payload schema validation failed: {e.message}")

    def validate_output(self, payload: Dict[str, Any]) -> None:
        try:
            jsonschema.validate(instance=payload, schema=self.output_schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Output payload schema validation failed: {e.message}")

@dataclass(frozen=True)
class ExecutionSchema:
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    required_json_mode: bool = False
    required_tool_calling: bool = False
    required_streaming: bool = False
    required_context_window: int = 8192
    required_structured_output: bool = True
    required_reasoning_support: bool = False

@dataclass(frozen=True)
class CapabilityDependency:
    dependency_id: str  # UUIDv4 version ID
    dependency_urn: str # e.g. urn:karsa:capability:core:diff:1.0.0

@dataclass(frozen=True)
class ContractFingerprint:
    sha256_hash: str

    @classmethod
    def generate(cls, input_schema: Dict[str, Any], output_schema: Dict[str, Any]) -> "ContractFingerprint":
        normalized_input = json.dumps(input_schema, sort_keys=True)
        normalized_output = json.dumps(output_schema, sort_keys=True)
        combined = f"input:{normalized_input}|output:{normalized_output}"
        hasher = hashlib.sha256(combined.encode("utf-8"))
        return cls(sha256_hash=hasher.hexdigest())

class ImmutableList(list):
    def __init__(self, iterable, parent, attr_name):
        super().__init__(iterable)
        self._parent = parent
        self._attr_name = attr_name

    def _check(self):
        if hasattr(self._parent, "_check_immutability"):
            self._parent._check_immutability()

    def append(self, item):
        self._check()
        super().append(item)

    def extend(self, iterable):
        self._check()
        super().extend(iterable)

    def insert(self, index, item):
        self._check()
        super().insert(index, item)

    def pop(self, index=-1):
        self._check()
        return super().pop(index)

    def remove(self, item):
        self._check()
        super().remove(item)

    def clear(self):
        self._check()
        super().clear()

    def __setitem__(self, key, value):
        self._check()
        super().__setitem__(key, value)

    def __delitem__(self, key):
        self._check()
        super().__delitem__(key)

@dataclass
class CapabilityDefinition(VersionedAggregate):
    capability_id: str = ""
    capability_family_id: str = ""
    urn: Optional[CapabilityURN] = None
    owner: Optional[CapabilityOwner] = None
    state: CapabilityLifecycleState = CapabilityLifecycleState.DRAFT
    schema_contract: Optional[ExecutionSchema] = None
    contract_fingerprint: Optional[ContractFingerprint] = None
    dependencies: List[CapabilityDependency] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __setattr__(self, name: str, value: Any) -> None:
        prop = getattr(self.__class__, name, None)
        if isinstance(prop, property) and prop.fset is None:
            raise AttributeError("can't set attribute")
        if "updated_at" in self.__dict__ and name not in ("state", "updated_at", "aggregate_version"):
            self._check_immutability()
        if name == "dependencies" and not isinstance(value, ImmutableList):
            value = ImmutableList(value or [], self, name)
        super().__setattr__(name, value)

    @property
    def contract(self) -> Optional[ExecutionContract]:
        if not self.schema_contract:
            return None
        return ExecutionContract(
            input_schema=self.schema_contract.input_schema,
            output_schema=self.schema_contract.output_schema,
            preconditions=self.schema_contract.preconditions,
            postconditions=self.schema_contract.postconditions
        )

    def _check_immutability(self) -> None:
        if self.state in (CapabilityLifecycleState.ACTIVE, CapabilityLifecycleState.DEPRECATED,
                          CapabilityLifecycleState.RETIRED, CapabilityLifecycleState.REVOKED):
            raise ValueError("Cannot modify an active, deprecated, retired, or revoked capability definition.")

    def transition_to(self, new_state: CapabilityLifecycleState, reason: str = "") -> None:
        valid_transitions = {
            CapabilityLifecycleState.DRAFT: [CapabilityLifecycleState.REVIEW],
            CapabilityLifecycleState.REVIEW: [CapabilityLifecycleState.ACTIVE, CapabilityLifecycleState.RETIRED],
            CapabilityLifecycleState.ACTIVE: [CapabilityLifecycleState.DEPRECATED, CapabilityLifecycleState.SUSPENDED, CapabilityLifecycleState.REVOKED],
            CapabilityLifecycleState.SUSPENDED: [CapabilityLifecycleState.ACTIVE, CapabilityLifecycleState.REVOKED],
            CapabilityLifecycleState.DEPRECATED: [CapabilityLifecycleState.RETIRED],
            CapabilityLifecycleState.RETIRED: [],
            CapabilityLifecycleState.REVOKED: []
        }
        
        allowed = valid_transitions.get(self.state, [])
        if new_state not in allowed:
            raise ValueError(f"Invalid state transition from {self.state.name} to {new_state.name}")
            
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)
        self.increment_version()

    def validate_input(self, payload: Dict[str, Any]) -> None:
        if not self.schema_contract:
            raise ValueError("Execution schema contract not defined.")
        # Re-use ExecutionContract validation
        contract = self.contract
        if contract:
            contract.validate_input(payload)

    def validate_output(self, payload: Dict[str, Any]) -> None:
        if not self.schema_contract:
            raise ValueError("Execution schema contract not defined.")
        contract = self.contract
        if contract:
            contract.validate_output(payload)

@dataclass
class CapabilityExecution(VersionedAggregate):
    execution_id: str = ""
    capability_urn: Optional[CapabilityURN] = None
    correlation_id: str = ""
    causation_id: str = ""
    workspace_id: str = ""
    branch_id: str = ""
    status: ExecutionStatus = ExecutionStatus.QUEUED
    budget: ExecutionBudget = field(default_factory=ExecutionBudget)
    input_payload: Dict[str, Any] = field(default_factory=dict)
    output_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    telemetry: Optional[ExecutionTelemetry] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def start(self) -> None:
        if self.status != ExecutionStatus.QUEUED:
            raise ValueError(f"Cannot start execution in state {self.status.name}")
        self.status = ExecutionStatus.RUNNING
        self.increment_version()

    def complete(self, output_payload: Dict[str, Any], telemetry: ExecutionTelemetry) -> None:
        if self.status != ExecutionStatus.RUNNING:
            raise ValueError(f"Cannot complete execution in state {self.status.name}")
        self.status = ExecutionStatus.COMPLETED
        self.output_payload = output_payload
        self.telemetry = telemetry
        self.increment_version()

    def fail(self, error_message: str, telemetry: Optional[ExecutionTelemetry] = None) -> None:
        if self.status not in (ExecutionStatus.QUEUED, ExecutionStatus.RUNNING):
            raise ValueError(f"Cannot fail execution in state {self.status.name}")
        self.status = ExecutionStatus.FAILED
        self.error_message = error_message
        self.telemetry = telemetry
        self.increment_version()
