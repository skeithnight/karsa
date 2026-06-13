import uuid
import hashlib
from enum import Enum
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from karsa.shared.domain.aggregate import VersionedAggregate

class PolicyLifecycleState(Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    RETIRED = "RETIRED"

class PolicyAction(Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    WARN = "WARN"

@dataclass(frozen=True)
class PolicyId:
    value: str

@dataclass(frozen=True)
class PolicyVersion:
    value: str  # e.g., "1.0.0"

@dataclass(frozen=True)
class DecisionReason:
    value: str

@dataclass(frozen=True)
class PolicyURN:
    namespace: str
    name: str
    version: str

    def to_string(self) -> str:
        return f"urn:karsa:policy:{self.namespace}:{self.name}:{self.version}"

    @classmethod
    def from_string(cls, urn_str: str) -> "PolicyURN":
        if not urn_str.startswith("urn:karsa:policy:"):
            raise ValueError(f"Invalid policy URN prefix: {urn_str}")
        parts = urn_str[len("urn:karsa:policy:"):].split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid policy URN format: {urn_str}. Expected namespace:name:version")
        if not parts[0] or not parts[1] or not parts[2]:
            raise ValueError(f"Policy URN components cannot be empty: {urn_str}")
        return cls(namespace=parts[0], name=parts[1], version=parts[2])

@dataclass(frozen=True)
class PolicyScope:
    target_type: str  # e.g., "WORKFLOW", "CAPABILITY", "PROVIDER"
    target_urn: str   # e.g., "urn:karsa:capability:chat:v1" or "*"

@dataclass(frozen=True)
class PolicyCondition:
    attribute: str     # e.g., "estimated_cost", "execution_time"
    operator: str      # e.g., "LESS_THAN_OR_EQUAL", "EQUALS"
    value: str         # e.g., "0.05" or "ACTIVE"

    def evaluate(self, context: Dict[str, Any]) -> bool:
        if self.attribute not in context:
            return False
        ctx_val = context[self.attribute]
        op = self.operator

        try:
            # Handle float comparison
            if op == "LESS_THAN_OR_EQUAL":
                return float(ctx_val) <= float(self.value)
            elif op == "GREATER_THAN":
                return float(ctx_val) > float(self.value)
            elif op == "EQUALS":
                return str(ctx_val) == str(self.value)
        except (ValueError, TypeError):
            return False
        return False

@dataclass(frozen=True)
class BudgetConstraint:
    limit_usd: float
    time_window_seconds: int

@dataclass
class PolicyRule:
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    condition: Optional[PolicyCondition] = None
    action: PolicyAction = PolicyAction.DENY
    priority: int = 100

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
class PolicyDefinition(VersionedAggregate):
    policy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    policy_urn: Optional[PolicyURN] = None
    state: PolicyLifecycleState = PolicyLifecycleState.DRAFT
    priority: int = 100
    scope: Optional[PolicyScope] = None
    rules: List[PolicyRule] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __setattr__(self, name: str, value: Any) -> None:
        prop = getattr(self.__class__, name, None)
        if isinstance(prop, property) and prop.fset is None:
            raise AttributeError("can't set attribute")
        if "updated_at" in self.__dict__ and name not in ("state", "updated_at", "aggregate_version"):
            self._check_immutability()
        if name == "rules" and not isinstance(value, ImmutableList):
            value = ImmutableList(value or [], self, name)
        super().__setattr__(name, value)

    def _check_immutability(self) -> None:
        if self.state not in (PolicyLifecycleState.DRAFT, PolicyLifecycleState.REVIEW):
            raise ValueError(f"Cannot modify policy definition in state {self.state.name}")

    def transition_to(self, new_state: PolicyLifecycleState, reason: str = "") -> None:
        valid_transitions = {
            PolicyLifecycleState.DRAFT: [PolicyLifecycleState.REVIEW],
            PolicyLifecycleState.REVIEW: [PolicyLifecycleState.ACTIVE, PolicyLifecycleState.RETIRED],
            PolicyLifecycleState.ACTIVE: [PolicyLifecycleState.SUSPENDED, PolicyLifecycleState.REVOKED, PolicyLifecycleState.RETIRED],
            PolicyLifecycleState.SUSPENDED: [PolicyLifecycleState.ACTIVE, PolicyLifecycleState.RETIRED],
            PolicyLifecycleState.REVOKED: [PolicyLifecycleState.RETIRED],
            PolicyLifecycleState.RETIRED: [],
        }

        allowed = valid_transitions.get(self.state, [])
        if new_state not in allowed:
            raise ValueError(f"Invalid policy transition from {self.state.name} to {new_state.name}")

        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)
        self.increment_version()

@dataclass
class GovernanceDecision(VersionedAggregate):
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str = ""
    outcome: str = "DENIED"  # APPROVED, DENIED
    reason: str = ""
    estimated_cost: float = 0.0
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class GovernanceAuditChain(VersionedAggregate):
    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    previous_hash: str = ""
    current_hash: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def calculate_hash(decision_id: str, outcome: str, previous_hash: str) -> str:
        payload = f"{decision_id}|{outcome}|{previous_hash}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

@dataclass
class GovernanceBudgetCache:
    workflow_id: str
    remaining_budget: float
    last_updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_stale(self, max_stale_limit_seconds: int = 60) -> bool:
        age = (datetime.now(timezone.utc) - self.last_updated_at).total_seconds()
        return age > max_stale_limit_seconds
