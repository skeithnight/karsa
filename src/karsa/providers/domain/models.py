import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from karsa.shared.domain.aggregate import VersionedAggregate

class ProviderLifecycleState(Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    SUSPENDED = "SUSPENDED"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"

class ProviderHealthStatus(Enum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    SUSPENDED = "SUSPENDED"

class CompatibilityResult(Enum):
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"

class RoutingPolicy(Enum):
    LOWEST_COST = "LOWEST_COST"
    LOWEST_LATENCY = "LOWEST_LATENCY"
    HIGHEST_HEALTH = "HIGHEST_HEALTH"

@dataclass(frozen=True)
class ProviderURN:
    vendor: str
    model: str
    version: str

    def to_string(self) -> str:
        return f"urn:karsa:provider:{self.vendor}:{self.model}:{self.version}"

    @classmethod
    def from_string(cls, urn_str: str) -> "ProviderURN":
        if not urn_str.startswith("urn:karsa:provider:"):
            raise ValueError(f"Invalid provider URN prefix: {urn_str}")
        parts = urn_str[len("urn:karsa:provider:"):].split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid provider URN format: {urn_str}. Expected vendor:model:version")
        if not parts[0] or not parts[1] or not parts[2]:
            raise ValueError(f"Provider URN components cannot be empty: {urn_str}")
        return cls(vendor=parts[0], model=parts[1], version=parts[2])

@dataclass(frozen=True)
class ProviderPricing:
    input_rate_per_1m: float
    output_rate_per_1m: float
    currency: str = "USD"

@dataclass(frozen=True)
class CapabilityRequirement:
    json_mode: bool
    tool_calling: bool
    streaming: bool
    structured_output: bool
    reasoning_support: bool
    min_context_window: int

@dataclass
class ProviderCapabilityMapping:
    mapping_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    capability_urn: str = ""
    json_mode: bool = True
    tool_calling: bool = True
    streaming: bool = True
    context_window: int = 8192
    structured_output: bool = True
    reasoning_support: bool = False

    def evaluate_compatibility(self, requirements: CapabilityRequirement) -> bool:
        if requirements.json_mode and not self.json_mode:
            return False
        if requirements.tool_calling and not self.tool_calling:
            return False
        if requirements.streaming and not self.streaming:
            return False
        if requirements.structured_output and not self.structured_output:
            return False
        if requirements.reasoning_support and not self.reasoning_support:
            return False
        if self.context_window < requirements.min_context_window:
            return False
        return True

@dataclass(frozen=True)
class ProviderRoutingDecision:
    provider_id: str
    provider_urn: str
    fallback_chain: List[str]
    routing_policy: RoutingPolicy
    estimated_cost: float = 0.0

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
class ProviderDefinition(VersionedAggregate):
    provider_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    provider_urn: Optional[ProviderURN] = None
    state: ProviderLifecycleState = ProviderLifecycleState.DRAFT
    pricing: Optional[ProviderPricing] = None
    capability_mappings: List[ProviderCapabilityMapping] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __setattr__(self, name: str, value: Any) -> None:
        prop = getattr(self.__class__, name, None)
        if isinstance(prop, property) and prop.fset is None:
            raise AttributeError("can't set attribute")
        if "updated_at" in self.__dict__ and name not in ("state", "updated_at", "aggregate_version"):
            self._check_immutability()
        if name == "capability_mappings" and not isinstance(value, ImmutableList):
            value = ImmutableList(value or [], self, name)
        super().__setattr__(name, value)

    def _check_immutability(self) -> None:
        if self.state not in (ProviderLifecycleState.DRAFT, ProviderLifecycleState.REVIEW):
            raise ValueError(f"Cannot modify stable provider configuration in state {self.state.name}")

    def transition_to(self, new_state: ProviderLifecycleState, reason: str = "") -> None:
        valid_transitions = {
            ProviderLifecycleState.DRAFT: [ProviderLifecycleState.REVIEW],
            ProviderLifecycleState.REVIEW: [ProviderLifecycleState.ACTIVE, ProviderLifecycleState.RETIRED],
            ProviderLifecycleState.ACTIVE: [ProviderLifecycleState.DEGRADED, ProviderLifecycleState.SUSPENDED, ProviderLifecycleState.DEPRECATED, ProviderLifecycleState.RETIRED],
            ProviderLifecycleState.DEGRADED: [ProviderLifecycleState.ACTIVE, ProviderLifecycleState.SUSPENDED, ProviderLifecycleState.DEPRECATED, ProviderLifecycleState.RETIRED],
            ProviderLifecycleState.SUSPENDED: [ProviderLifecycleState.ACTIVE, ProviderLifecycleState.REVIEW, ProviderLifecycleState.RETIRED],
            ProviderLifecycleState.DEPRECATED: [ProviderLifecycleState.RETIRED],
            ProviderLifecycleState.RETIRED: [],
        }

        allowed = valid_transitions.get(self.state, [])
        if new_state not in allowed:
            raise ValueError(f"Invalid transition from {self.state.name} to {new_state.name}")

        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)
        self.increment_version()

@dataclass
class ProviderHealthState(VersionedAggregate):
    provider_id: str = ""
    health_status: ProviderHealthStatus = ProviderHealthStatus.ACTIVE
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    average_latency_ms: float = 0.0
    last_failure_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    degraded_threshold: int = 3
    suspended_threshold: int = 5

    def record_success(self, latency_ms: float) -> Optional[ProviderHealthStatus]:
        prev_status = self.health_status
        self.success_count += 1
        
        # Recalculate rolling average latency
        total_requests = self.success_count + self.failure_count
        self.average_latency_ms = ((self.average_latency_ms * (total_requests - 1)) + latency_ms) / total_requests
        
        self.consecutive_failures = 0
        self.last_success_at = datetime.now(timezone.utc)

        # Recover to ACTIVE if currently degraded/suspended
        if self.health_status != ProviderHealthStatus.ACTIVE:
            self.health_status = ProviderHealthStatus.ACTIVE

        self.increment_version()
        return prev_status if prev_status != self.health_status else None

    def record_failure(self, latency_ms: float) -> Optional[ProviderHealthStatus]:
        prev_status = self.health_status
        self.failure_count += 1
        
        # Recalculate rolling average latency
        total_requests = self.success_count + self.failure_count
        self.average_latency_ms = ((self.average_latency_ms * (total_requests - 1)) + latency_ms) / total_requests
        
        self.consecutive_failures += 1
        self.last_failure_at = datetime.now(timezone.utc)

        # Transition health status based on consecutive failures
        if self.consecutive_failures >= self.suspended_threshold:
            self.health_status = ProviderHealthStatus.SUSPENDED
        elif self.consecutive_failures >= self.degraded_threshold:
            self.health_status = ProviderHealthStatus.DEGRADED

        self.increment_version()
        return prev_status if prev_status != self.health_status else None
