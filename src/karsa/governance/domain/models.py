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
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"

class PolicyAction(Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"

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
    target_type: str  # PORTFOLIO, SECTOR, ASSET, CAPABILITY, WORKFLOW
    target_urn: str   # URN or "*"

@dataclass(frozen=True)
class PolicyCondition:
    attribute: str     # e.g., "portfolio_var_95", "estimated_cost"
    operator: str      # e.g., "LESS_THAN_OR_EQUAL", "GREATER_THAN", "EQUALS"
    value: str         # limit threshold value

    def evaluate(self, context: Dict[str, Any]) -> bool:
        if self.attribute not in context:
            return False
        ctx_val = context[self.attribute]
        op = self.operator

        try:
            # Handle numeric conversion & float comparison
            if op == "LESS_THAN_OR_EQUAL":
                return float(ctx_val) <= float(self.value)
            elif op == "GREATER_THAN":
                return float(ctx_val) > float(self.value)
            elif op == "EQUALS":
                return str(ctx_val) == str(self.value)
        except (ValueError, TypeError):
            return False
        return False

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
class CompliancePolicy(VersionedAggregate):
    row_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    policy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    policy_urn: Optional[PolicyURN] = None
    state: PolicyLifecycleState = PolicyLifecycleState.DRAFT
    priority: int = 100
    scope: Optional[PolicyScope] = None
    rules: List[PolicyRule] = field(default_factory=list)
    signature_block: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __setattr__(self, name: str, value: Any) -> None:
        if "updated_at" in self.__dict__ and name not in ("state", "updated_at", "aggregate_version", "signature_block"):
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
            PolicyLifecycleState.REVIEW: [PolicyLifecycleState.APPROVED, PolicyLifecycleState.RETIRED],
            PolicyLifecycleState.APPROVED: [PolicyLifecycleState.ACTIVE, PolicyLifecycleState.RETIRED],
            PolicyLifecycleState.ACTIVE: [PolicyLifecycleState.RETIRED],
            PolicyLifecycleState.RETIRED: [],
        }

        allowed = valid_transitions.get(self.state, [])
        if new_state not in allowed:
            raise ValueError(f"Invalid policy transition from {self.state.name} to {new_state.name}")

        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)
        self.increment_version()

# Compatibility alias for legacy tests
PolicyDefinition = CompliancePolicy

@dataclass
class AuthorizationPolicy(VersionedAggregate):
    policy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    policy_urn: str = "" # e.g. urn:karsa:auth-policy:<name>:<version>
    state: str = "ACTIVE" # ACTIVE, RETIRED
    roles_mapping: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ExceptionToken(VersionedAggregate):
    token_hash: str = "" # Primary key
    token_urn: str = ""
    order_id: str = ""
    state: str = "" # REQUESTED, APPROVED, ACTIVE, EXPIRED, REVOKED
    target_type: str = ""
    target_urn: str = ""
    limit_parameter: str = ""
    limit_ceiling: float = 0.0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expire_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cio_signature: str = ""
    compliance_signature: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def generate_token_hash(payload: Dict[str, Any]) -> str:
        # Serializes payload deterministically and computes SHA-256
        import json
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

@dataclass
class ExceptionRevocation(VersionedAggregate):
    revocation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    token_hash: str = ""
    revoked_by: str = ""
    revoked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""

@dataclass
class GovernanceDecisionRecord(VersionedAggregate):
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    decision_outcome: str = "DENY" # ALLOW, DENY, ALLOW_VIA_EXCEPTION
    policy_version_urn: Optional[str] = None
    exception_token_urn: Optional[str] = None
    portfolio_snapshot_id: str = ""
    risk_evaluation_id: str = ""
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Legacy compatibility fields
    execution_id: str = ""
    outcome: str = ""
    reason: str = ""
    estimated_cost: float = 0.0

    def __post_init__(self):
        # Align compatibility fields
        if self.execution_id and not self.order_id:
            self.order_id = self.execution_id
        elif self.order_id and not self.execution_id:
            self.execution_id = self.order_id

        if self.outcome and not self.decision_outcome:
            if self.outcome == "APPROVED":
                self.decision_outcome = "ALLOW"
            elif self.outcome == "DENIED":
                self.decision_outcome = "DENY"
        elif self.decision_outcome and not self.outcome:
            self.outcome = "APPROVED" if self.decision_outcome in ("ALLOW", "ALLOW_VIA_EXCEPTION") else "DENIED"

# Compatibility alias for legacy tests
GovernanceDecision = GovernanceDecisionRecord

@dataclass
class RiskStateSnapshot:
    portfolio_snapshot_id: str
    risk_metrics: Dict[str, Any] = field(default_factory=dict)
    concentration_stats: Dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cached_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_stale(self, max_stale_limit_seconds: int = 600) -> bool:
        # Check staleness against evaluated_at timestamp
        age = (datetime.now(timezone.utc) - self.evaluated_at).total_seconds()
        return age > max_stale_limit_seconds

# Compatibility models for legacy tests
@dataclass
class GovernanceBudgetCache:
    workflow_id: str
    remaining_budget: float
    last_updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_stale(self, max_stale_limit_seconds: int = 60) -> bool:
        age = (datetime.now(timezone.utc) - self.last_updated_at).total_seconds()
        return age > max_stale_limit_seconds

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
