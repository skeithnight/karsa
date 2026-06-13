import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from karsa.shared.infrastructure.uow import ConcurrencyConflictError
from karsa.governance.domain.repositories import (
    PolicyDefinitionRepository, GovernanceDecisionRepository, 
    GovernanceAuditRepository, GovernanceBudgetCacheRepository
)
from karsa.governance.domain.models import (
    PolicyDefinition, PolicyURN, PolicyScope, PolicyCondition, PolicyAction,
    PolicyRule, GovernanceDecision, GovernanceAuditChain, GovernanceBudgetCache,
    ImmutableList
)

# ----------------- Serialization & Deserialization Helpers -----------------

def serialize_policy_definition(policy: PolicyDefinition) -> Dict[str, Any]:
    rules_data = []
    for r in policy.rules:
        cond_data = None
        if r.condition:
            cond_data = {
                "attribute": r.condition.attribute,
                "operator": r.condition.operator,
                "value": r.condition.value
            }
        rules_data.append({
            "rule_id": r.rule_id,
            "condition": cond_data,
            "action": r.action.value,
            "priority": r.priority
        })

    return {
        "policy_id": policy.policy_id,
        "policy_urn": policy.policy_urn.to_string() if policy.policy_urn else None,
        "state": policy.state.value,
        "priority": policy.priority,
        "scope": {
            "target_type": policy.scope.target_type,
            "target_urn": policy.scope.target_urn
        } if policy.scope else None,
        "rules": rules_data,
        "aggregate_version": policy.aggregate_version,
        "created_at": policy.created_at.isoformat(),
        "updated_at": policy.updated_at.isoformat()
    }

def deserialize_policy_definition(data: Dict[str, Any]) -> PolicyDefinition:
    urn = PolicyURN.from_string(data["policy_urn"]) if data.get("policy_urn") else None
    scope = None
    if data.get("scope"):
        scope = PolicyScope(
            target_type=data["scope"]["target_type"],
            target_urn=data["scope"]["target_urn"]
        )
    rules = []
    for r in data.get("rules", []):
        cond = None
        if r.get("condition"):
            cond = PolicyCondition(
                attribute=r["condition"]["attribute"],
                operator=r["condition"]["operator"],
                value=r["condition"]["value"]
            )
        rules.append(PolicyRule(
            rule_id=r["rule_id"],
            condition=cond,
            action=PolicyAction(r["action"]),
            priority=r.get("priority", 100)
        ))

    policy = PolicyDefinition(
        policy_id=data["policy_id"],
        policy_urn=urn,
        priority=data.get("priority", 100),
        scope=scope,
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"])
    )
    object.__setattr__(policy, "state", PolicyLifecycleState(data["state"]))
    object.__setattr__(policy, "rules", ImmutableList(rules, policy, "rules"))
    object.__setattr__(policy, "aggregate_version", data.get("aggregate_version", 0))
    return policy

from karsa.governance.domain.models import PolicyLifecycleState

def serialize_governance_decision(decision: GovernanceDecision) -> Dict[str, Any]:
    return {
        "decision_id": decision.decision_id,
        "execution_id": decision.execution_id,
        "outcome": decision.outcome,
        "reason": decision.reason,
        "estimated_cost": decision.estimated_cost,
        "evaluated_at": decision.evaluated_at.isoformat(),
        "aggregate_version": decision.aggregate_version
    }

def deserialize_governance_decision(data: Dict[str, Any]) -> GovernanceDecision:
    decision = GovernanceDecision(
        decision_id=data["decision_id"],
        execution_id=data["execution_id"],
        outcome=data["outcome"],
        reason=data["reason"],
        estimated_cost=data.get("estimated_cost", 0.0),
        evaluated_at=datetime.fromisoformat(data["evaluated_at"])
    )
    object.__setattr__(decision, "aggregate_version", data.get("aggregate_version", 0))
    return decision

def serialize_governance_audit_chain(chain: GovernanceAuditChain) -> Dict[str, Any]:
    return {
        "audit_id": chain.audit_id,
        "decision_id": chain.decision_id,
        "previous_hash": chain.previous_hash,
        "current_hash": chain.current_hash,
        "timestamp": chain.timestamp.isoformat(),
        "aggregate_version": chain.aggregate_version
    }

def deserialize_governance_audit_chain(data: Dict[str, Any]) -> GovernanceAuditChain:
    chain = GovernanceAuditChain(
        audit_id=data["audit_id"],
        decision_id=data["decision_id"],
        previous_hash=data["previous_hash"],
        current_hash=data["current_hash"],
        timestamp=datetime.fromisoformat(data["timestamp"])
    )
    object.__setattr__(chain, "aggregate_version", data.get("aggregate_version", 0))
    return chain

def serialize_governance_budget_cache(cache: GovernanceBudgetCache) -> Dict[str, Any]:
    return {
        "workflow_id": cache.workflow_id,
        "remaining_budget": cache.remaining_budget,
        "last_updated_at": cache.last_updated_at.isoformat()
    }

def deserialize_governance_budget_cache(data: Dict[str, Any]) -> GovernanceBudgetCache:
    return GovernanceBudgetCache(
        workflow_id=data["workflow_id"],
        remaining_budget=data["remaining_budget"],
        last_updated_at=datetime.fromisoformat(data["last_updated_at"])
    )


# ----------------- InMemory Repositories -----------------

class InMemoryPolicyDefinitionRepository(PolicyDefinitionRepository):
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}

    def save(self, policy: PolicyDefinition) -> None:
        policy_id = policy.policy_id
        if policy_id in self._data:
            stored = self._data[policy_id]
            stored_version = stored["aggregate_version"]
            if stored_version != policy.aggregate_version and stored_version != policy.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict on PolicyDefinition {policy_id}: "
                    f"stored version {stored_version}, saving version {policy.aggregate_version}"
                )
        self._data[policy_id] = serialize_policy_definition(policy)

    def find_by_id(self, policy_id: str) -> Optional[PolicyDefinition]:
        data = self._data.get(policy_id)
        if not data:
            return None
        return deserialize_policy_definition(data)

    def find_by_urn(self, urn: PolicyURN) -> Optional[PolicyDefinition]:
        urn_str = urn.to_string()
        for data in self._data.values():
            if data.get("policy_urn") == urn_str:
                return deserialize_policy_definition(data)
        return None

    def find_active_for_scope(self, target_type: str, target_urn: str) -> List[PolicyDefinition]:
        active_policies = []
        for data in self._data.values():
            if data["state"] == PolicyLifecycleState.ACTIVE.value:
                scope = data.get("scope")
                if scope and scope["target_type"] == target_type:
                    # Scope matches if it is a wildcard '*' or exact match
                    if scope["target_urn"] == "*" or scope["target_urn"] == target_urn:
                        active_policies.append(deserialize_policy_definition(data))
        return active_policies


class InMemoryGovernanceDecisionRepository(GovernanceDecisionRepository):
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}

    def save(self, decision: GovernanceDecision) -> None:
        decision_id = decision.decision_id
        if decision_id in self._data:
            stored = self._data[decision_id]
            stored_version = stored["aggregate_version"]
            if stored_version != decision.aggregate_version and stored_version != decision.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict on GovernanceDecision {decision_id}: "
                    f"stored version {stored_version}, saving version {decision.aggregate_version}"
                )
        self._data[decision_id] = serialize_governance_decision(decision)

    def find_by_id(self, decision_id: str) -> Optional[GovernanceDecision]:
        data = self._data.get(decision_id)
        if not data:
            return None
        return deserialize_governance_decision(data)


class InMemoryGovernanceAuditRepository(GovernanceAuditRepository):
    def __init__(self):
        self._list: List[Dict[str, Any]] = []

    def append_chain(self, entry: GovernanceAuditChain) -> None:
        # Check if already present to prevent duplicates and do simple OCC check if re-saved
        for stored in self._list:
            if stored["audit_id"] == entry.audit_id:
                stored_version = stored["aggregate_version"]
                if stored_version != entry.aggregate_version and stored_version != entry.aggregate_version - 1:
                    raise ConcurrencyConflictError(f"Concurrency conflict on GovernanceAuditChain {entry.audit_id}")
                stored.update(serialize_governance_audit_chain(entry))
                return
        self._list.append(serialize_governance_audit_chain(entry))

    def get_latest_entry(self) -> Optional[GovernanceAuditChain]:
        if not self._list:
            return None
        # Retrieve the last item in the chained log
        return deserialize_governance_audit_chain(self._list[-1])


class InMemoryGovernanceBudgetCacheRepository(GovernanceBudgetCacheRepository):
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}

    def save(self, cache: GovernanceBudgetCache) -> None:
        self._data[cache.workflow_id] = serialize_governance_budget_cache(cache)

    def find_by_workflow_id(self, workflow_id: str) -> Optional[GovernanceBudgetCache]:
        data = self._data.get(workflow_id)
        if not data:
            return None
        return deserialize_governance_budget_cache(data)


# ----------------- File Repositories -----------------

class FilePolicyDefinitionRepository(PolicyDefinitionRepository):
    def __init__(self, workspace_path: Optional[Path] = None):
        self.base_dir = Path(workspace_path or ".").resolve() / ".karsa" / "governance" / "policies"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, policy_id: str) -> Path:
        return self.base_dir / f"{policy_id}.json"

    def save(self, policy: PolicyDefinition) -> None:
        path = self._get_path(policy.policy_id)
        if path.exists():
            try:
                with open(path, "r") as f:
                    stored = json.load(f)
                stored_version = stored.get("aggregate_version", 0)
                if stored_version != policy.aggregate_version and stored_version != policy.aggregate_version - 1:
                    raise ConcurrencyConflictError(
                        f"Concurrency conflict on PolicyDefinition {policy.policy_id}: "
                        f"stored version {stored_version}, saving version {policy.aggregate_version}"
                    )
            except (json.JSONDecodeError, OSError):
                pass
        serialized_data = serialize_policy_definition(policy)
        with open(path, "w") as f:
            json.dump(serialized_data, f, indent=2)

    def find_by_id(self, policy_id: str) -> Optional[PolicyDefinition]:
        path = self._get_path(policy_id)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return deserialize_policy_definition(data)
        except Exception:
            return None

    def find_by_urn(self, urn: PolicyURN) -> Optional[PolicyDefinition]:
        urn_str = urn.to_string()
        if not self.base_dir.exists():
            return None
        for filename in os.listdir(self.base_dir):
            if filename.endswith(".json"):
                path = self.base_dir / filename
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    if data.get("policy_urn") == urn_str:
                        return deserialize_policy_definition(data)
                except Exception:
                    continue
        return None

    def find_active_for_scope(self, target_type: str, target_urn: str) -> List[PolicyDefinition]:
        active_policies = []
        if not self.base_dir.exists():
            return []
        for filename in os.listdir(self.base_dir):
            if filename.endswith(".json"):
                path = self.base_dir / filename
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    if data.get("state") == PolicyLifecycleState.ACTIVE.value:
                        scope = data.get("scope")
                        if scope and scope["target_type"] == target_type:
                            if scope["target_urn"] == "*" or scope["target_urn"] == target_urn:
                                active_policies.append(deserialize_policy_definition(data))
                except Exception:
                    continue
        return active_policies


class FileGovernanceDecisionRepository(GovernanceDecisionRepository):
    def __init__(self, workspace_path: Optional[Path] = None):
        self.base_dir = Path(workspace_path or ".").resolve() / ".karsa" / "governance" / "decisions"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, decision_id: str) -> Path:
        return self.base_dir / f"{decision_id}.json"

    def save(self, decision: GovernanceDecision) -> None:
        path = self._get_path(decision.decision_id)
        if path.exists():
            try:
                with open(path, "r") as f:
                    stored = json.load(f)
                stored_version = stored.get("aggregate_version", 0)
                if stored_version != decision.aggregate_version and stored_version != decision.aggregate_version - 1:
                    raise ConcurrencyConflictError(
                        f"Concurrency conflict on GovernanceDecision {decision.decision_id}: "
                        f"stored version {stored_version}, saving version {decision.aggregate_version}"
                    )
            except (json.JSONDecodeError, OSError):
                pass
        serialized_data = serialize_governance_decision(decision)
        with open(path, "w") as f:
            json.dump(serialized_data, f, indent=2)

    def find_by_id(self, decision_id: str) -> Optional[GovernanceDecision]:
        path = self._get_path(decision_id)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return deserialize_governance_decision(data)
        except Exception:
            return None


class FileGovernanceAuditRepository(GovernanceAuditRepository):
    def __init__(self, workspace_path: Optional[Path] = None):
        self.base_dir = Path(workspace_path or ".").resolve() / ".karsa" / "governance" / "audit"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, audit_id: str) -> Path:
        return self.base_dir / f"{audit_id}.json"

    def append_chain(self, entry: GovernanceAuditChain) -> None:
        path = self._get_path(entry.audit_id)
        if path.exists():
            try:
                with open(path, "r") as f:
                    stored = json.load(f)
                stored_version = stored.get("aggregate_version", 0)
                if stored_version != entry.aggregate_version and stored_version != entry.aggregate_version - 1:
                    raise ConcurrencyConflictError(
                        f"Concurrency conflict on GovernanceAuditChain {entry.audit_id}: "
                        f"stored version {stored_version}, saving version {entry.aggregate_version}"
                    )
            except (json.JSONDecodeError, OSError):
                pass
        serialized_data = serialize_governance_audit_chain(entry)
        with open(path, "w") as f:
            json.dump(serialized_data, f, indent=2)

    def get_latest_entry(self) -> Optional[GovernanceAuditChain]:
        if not self.base_dir.exists():
            return None
        files = []
        for filename in os.listdir(self.base_dir):
            if filename.endswith(".json"):
                path = self.base_dir / filename
                files.append(path)
        if not files:
            return None
        # Sort files by their timestamp/creation time to get the latest
        try:
            entries = []
            for path in files:
                with open(path, "r") as f:
                    data = json.load(f)
                entries.append(deserialize_governance_audit_chain(data))
            # Sort by timestamp ascending, return the last
            entries.sort(key=lambda e: e.timestamp)
            return entries[-1]
        except Exception:
            return None


class FileGovernanceBudgetCacheRepository(GovernanceBudgetCacheRepository):
    def __init__(self, workspace_path: Optional[Path] = None):
        self.base_dir = Path(workspace_path or ".").resolve() / ".karsa" / "governance" / "budget_cache"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, workflow_id: str) -> Path:
        return self.base_dir / f"{workflow_id}.json"

    def save(self, cache: GovernanceBudgetCache) -> None:
        path = self._get_path(cache.workflow_id)
        serialized_data = serialize_governance_budget_cache(cache)
        with open(path, "w") as f:
            json.dump(serialized_data, f, indent=2)

    def find_by_workflow_id(self, workflow_id: str) -> Optional[GovernanceBudgetCache]:
        path = self._get_path(workflow_id)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return deserialize_governance_budget_cache(data)
        except Exception:
            return None
