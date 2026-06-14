import os
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import psycopg
import copy

from karsa.shared.infrastructure.uow import ConcurrencyConflictError
from karsa.governance.domain.repositories import (
    CompliancePolicyRepository, AuthorizationPolicyRepository, ExceptionTokenRepository,
    ExceptionRevocationRepository, GovernanceDecisionRecordRepository, RiskStateSnapshotRepository,
    GovernanceAuditRepository, GovernanceBudgetCacheRepository
)
from karsa.governance.domain.models import (
    CompliancePolicy, AuthorizationPolicy, ExceptionToken, ExceptionRevocation,
    GovernanceDecisionRecord, RiskStateSnapshot, PolicyURN, PolicyScope, PolicyCondition,
    PolicyRule, PolicyLifecycleState, PolicyAction, ImmutableList,
    GovernanceAuditChain, GovernanceBudgetCache
)

# ----------------- Serialization & Deserialization Helpers -----------------

def serialize_compliance_policy(policy: CompliancePolicy) -> Dict[str, Any]:
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
        "row_id": policy.row_id,
        "policy_id": policy.policy_id,
        "policy_urn": policy.policy_urn.to_string() if policy.policy_urn else None,
        "state": policy.state.value,
        "priority": policy.priority,
        "scope": {
            "target_type": policy.scope.target_type,
            "target_urn": policy.scope.target_urn
        } if policy.scope else None,
        "rules": rules_data,
        "signature_block": policy.signature_block,
        "aggregate_version": policy.aggregate_version,
        "created_at": policy.created_at.isoformat(),
        "updated_at": policy.updated_at.isoformat()
    }

def deserialize_compliance_policy(data: Dict[str, Any]) -> CompliancePolicy:
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

    import uuid
    policy = CompliancePolicy(
        row_id=data.get("row_id", str(uuid.uuid4())),
        policy_id=data["policy_id"],
        policy_urn=urn,
        priority=data.get("priority", 100),
        scope=scope,
        signature_block=data.get("signature_block"),
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"])
    )
    object.__setattr__(policy, "state", PolicyLifecycleState(data["state"]))
    object.__setattr__(policy, "rules", ImmutableList(rules, policy, "rules"))
    object.__setattr__(policy, "aggregate_version", data.get("aggregate_version", 0))
    return policy

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

class InMemoryCompliancePolicyRepository(CompliancePolicyRepository):
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}

    def save(self, policy: CompliancePolicy) -> None:
        policy_id = policy.policy_id
        if policy_id in self._data:
            stored = self._data[policy_id]
            stored_version = stored["aggregate_version"]
            if stored_version != policy.aggregate_version and stored_version != policy.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict on CompliancePolicy {policy_id}: "
                    f"stored version {stored_version}, saving version {policy.aggregate_version}"
                )
        self._data[policy_id] = serialize_compliance_policy(policy)

    def find_by_id(self, policy_id: str) -> Optional[CompliancePolicy]:
        data = self._data.get(policy_id)
        if not data:
            return None
        return deserialize_compliance_policy(data)

    def find_by_urn(self, urn: PolicyURN) -> Optional[CompliancePolicy]:
        return self.find_latest_by_urn(urn)

    def find_latest_by_urn(self, urn: PolicyURN) -> Optional[CompliancePolicy]:
        urn_str = urn.to_string()
        for data in self._data.values():
            if data.get("policy_urn") == urn_str:
                return deserialize_compliance_policy(data)
        return None

    def find_active_for_scope(self, target_type: str, target_urn: str) -> List[CompliancePolicy]:
        active_policies = []
        for data in self._data.values():
            if data["state"] == PolicyLifecycleState.ACTIVE.value:
                scope = data.get("scope")
                if scope and scope["target_type"] == target_type:
                    if scope["target_urn"] == "*" or scope["target_urn"] == target_urn:
                        active_policies.append(deserialize_compliance_policy(data))
        return active_policies

InMemoryPolicyDefinitionRepository = InMemoryCompliancePolicyRepository

class InMemoryAuthorizationPolicyRepository(AuthorizationPolicyRepository):
    def __init__(self):
        self._data: Dict[str, AuthorizationPolicy] = {}

    def save(self, policy: AuthorizationPolicy) -> None:
        self._data[policy.policy_id] = copy.deepcopy(policy)

    def find_by_id(self, policy_id: str) -> Optional[AuthorizationPolicy]:
        p = self._data.get(policy_id)
        return copy.deepcopy(p) if p else None

    def find_by_urn(self, urn_str: str) -> Optional[AuthorizationPolicy]:
        for p in self._data.values():
            if p.policy_urn == urn_str:
                return copy.deepcopy(p)
        return None

    def find_active_policy(self) -> Optional[AuthorizationPolicy]:
        for p in self._data.values():
            if p.state == "ACTIVE":
                return copy.deepcopy(p)
        return None

class InMemoryExceptionTokenRepository(ExceptionTokenRepository):
    def __init__(self):
        self._data: Dict[str, ExceptionToken] = {}

    def save(self, token: ExceptionToken) -> None:
        self._data[token.token_hash] = copy.deepcopy(token)

    def find_by_hash(self, token_hash: str) -> Optional[ExceptionToken]:
        t = self._data.get(token_hash)
        return copy.deepcopy(t) if t else None

    def find_active_by_order_id(self, order_id: str) -> Optional[ExceptionToken]:
        for t in self._data.values():
            if t.order_id == order_id and t.state == "ACTIVE":
                return copy.deepcopy(t)
        return None

class InMemoryExceptionRevocationRepository(ExceptionRevocationRepository):
    def __init__(self):
        self._data: Dict[str, ExceptionRevocation] = {}

    def save(self, revocation: ExceptionRevocation) -> None:
        self._data[revocation.token_hash] = copy.deepcopy(revocation)

    def find_by_token_hash(self, token_hash: str) -> Optional[ExceptionRevocation]:
        r = self._data.get(token_hash)
        return copy.deepcopy(r) if r else None

class InMemoryGovernanceDecisionRecordRepository(GovernanceDecisionRecordRepository):
    def __init__(self):
        self._data: Dict[str, GovernanceDecisionRecord] = {}

    def save(self, record: GovernanceDecisionRecord) -> None:
        self._data[record.decision_id] = copy.deepcopy(record)

    def find_by_id(self, decision_id: str) -> Optional[GovernanceDecisionRecord]:
        r = self._data.get(decision_id)
        return copy.deepcopy(r) if r else None

InMemoryGovernanceDecisionRepository = InMemoryGovernanceDecisionRecordRepository

class InMemoryRiskStateSnapshotRepository(RiskStateSnapshotRepository):
    def __init__(self):
        self._data: Dict[str, RiskStateSnapshot] = {}

    def save(self, snapshot: RiskStateSnapshot) -> None:
        self._data[snapshot.portfolio_snapshot_id] = copy.deepcopy(snapshot)

    def find_by_snapshot_id(self, portfolio_snapshot_id: str) -> Optional[RiskStateSnapshot]:
        s = self._data.get(portfolio_snapshot_id)
        return copy.deepcopy(s) if s else None

class InMemoryGovernanceAuditRepository(GovernanceAuditRepository):
    def __init__(self):
        self._list: List[Dict[str, Any]] = []

    def append_chain(self, entry: GovernanceAuditChain) -> None:
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


# ----------------- File Repositories (Compatibility) -----------------

class FileCompliancePolicyRepository(CompliancePolicyRepository):
    def __init__(self, workspace_path: Optional[Path] = None):
        self.base_dir = Path(workspace_path or ".").resolve() / ".karsa" / "governance" / "policies"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, policy_id: str) -> Path:
        return self.base_dir / f"{policy_id}.json"

    def save(self, policy: CompliancePolicy) -> None:
        path = self._get_path(policy.policy_id)
        if path.exists():
            try:
                with open(path, "r") as f:
                    stored = json.load(f)
                stored_version = stored.get("aggregate_version", 0)
                if stored_version != policy.aggregate_version and stored_version != policy.aggregate_version - 1:
                    raise ConcurrencyConflictError(
                        f"Concurrency conflict on CompliancePolicy {policy.policy_id}: "
                        f"stored version {stored_version}, saving version {policy.aggregate_version}"
                    )
            except (json.JSONDecodeError, OSError):
                pass
        serialized_data = serialize_compliance_policy(policy)
        with open(path, "w") as f:
            json.dump(serialized_data, f, indent=2)

    def find_by_id(self, policy_id: str) -> Optional[CompliancePolicy]:
        path = self._get_path(policy_id)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return deserialize_compliance_policy(data)
        except Exception:
            return None

    def find_by_urn(self, urn: PolicyURN) -> Optional[CompliancePolicy]:
        return self.find_latest_by_urn(urn)

    def find_latest_by_urn(self, urn: PolicyURN) -> Optional[CompliancePolicy]:
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
                        return deserialize_compliance_policy(data)
                except Exception:
                    continue
        return None

    def find_active_for_scope(self, target_type: str, target_urn: str) -> List[CompliancePolicy]:
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
                                active_policies.append(deserialize_compliance_policy(data))
                except Exception:
                    continue
        return active_policies

FilePolicyDefinitionRepository = FileCompliancePolicyRepository

class FileGovernanceDecisionRecordRepository(GovernanceDecisionRecordRepository):
    def __init__(self, workspace_path: Optional[Path] = None):
        self.base_dir = Path(workspace_path or ".").resolve() / ".karsa" / "governance" / "decisions"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, decision_id: str) -> Path:
        return self.base_dir / f"{decision_id}.json"

    def save(self, record: GovernanceDecisionRecord) -> None:
        path = self._get_path(record.decision_id)
        data = {
            "decision_id": record.decision_id,
            "order_id": record.order_id,
            "decision_outcome": record.decision_outcome,
            "policy_version_urn": record.policy_version_urn,
            "exception_token_urn": record.exception_token_urn,
            "portfolio_snapshot_id": record.portfolio_snapshot_id,
            "risk_evaluation_id": record.risk_evaluation_id,
            "evaluated_at": record.evaluated_at.isoformat()
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def find_by_id(self, decision_id: str) -> Optional[GovernanceDecisionRecord]:
        path = self._get_path(decision_id)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return GovernanceDecisionRecord(
                decision_id=data["decision_id"],
                order_id=data["order_id"],
                decision_outcome=data["decision_outcome"],
                policy_version_urn=data.get("policy_version_urn"),
                exception_token_urn=data.get("exception_token_urn"),
                portfolio_snapshot_id=data.get("portfolio_snapshot_id", ""),
                risk_evaluation_id=data.get("risk_evaluation_id", ""),
                evaluated_at=datetime.fromisoformat(data["evaluated_at"])
            )
        except Exception:
            return None

FileGovernanceDecisionRepository = FileGovernanceDecisionRecordRepository

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
        try:
            entries = []
            for path in files:
                with open(path, "r") as f:
                    data = json.load(f)
                entries.append(deserialize_governance_audit_chain(data))
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


# ----------------- Postgres Repositories -----------------

class PostgresCompliancePolicyRepository(CompliancePolicyRepository):
    def __init__(self, conn):
        self.conn = conn

    def save(self, policy: CompliancePolicy) -> None:
        rules_json = json.dumps([
            {
                "rule_id": r.rule_id,
                "condition": {
                    "attribute": r.condition.attribute,
                    "operator": r.condition.operator,
                    "value": r.condition.value
                } if r.condition else None,
                "action": r.action.value,
                "priority": r.priority
            }
            for r in policy.rules
        ])
        sig_json = json.dumps(policy.signature_block) if policy.signature_block else None
        
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO compliance_policies (
                    row_id, policy_id, policy_urn, state, priority, scope_type, scope_urn, rules, signature_block, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    policy.row_id,
                    policy.policy_id,
                    policy.policy_urn.to_string() if policy.policy_urn else None,
                    policy.state.value,
                    policy.priority,
                    policy.scope.target_type if policy.scope else None,
                    policy.scope.target_urn if policy.scope else None,
                    rules_json,
                    sig_json,
                    policy.created_at,
                    policy.updated_at
                )
            )

    def find_by_id(self, policy_id: str) -> Optional[CompliancePolicy]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT row_id, policy_id, policy_urn, state, priority, scope_type, scope_urn, rules, signature_block, created_at, updated_at
                FROM compliance_policies
                WHERE policy_id = %s
                ORDER BY created_at DESC LIMIT 1
                """,
                (policy_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_entity(row)

    def find_by_urn(self, urn: PolicyURN) -> Optional[CompliancePolicy]:
        return self.find_latest_by_urn(urn)

    def find_latest_by_urn(self, urn: PolicyURN) -> Optional[CompliancePolicy]:
        urn_str = urn.to_string()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT row_id, policy_id, policy_urn, state, priority, scope_type, scope_urn, rules, signature_block, created_at, updated_at
                FROM compliance_policies
                WHERE policy_urn = %s
                ORDER BY created_at DESC LIMIT 1
                """,
                (urn_str,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_entity(row)

    def find_active_for_scope(self, target_type: str, target_urn: str) -> List[CompliancePolicy]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT row_id, policy_id, policy_urn, state, priority, scope_type, scope_urn, rules, signature_block, created_at, updated_at
                FROM compliance_policies
                WHERE state = 'ACTIVE' AND scope_type = %s AND (scope_urn = '*' OR scope_urn = %s)
                """,
                (target_type, target_urn)
            )
            rows = cur.fetchall()
            return [self._row_to_entity(r) for r in rows]

    def _row_to_entity(self, row) -> CompliancePolicy:
        row_id, policy_id, policy_urn_str, state_str, priority, scope_type, scope_urn, rules_data, sig_data, created_at, updated_at = row
        urn = PolicyURN.from_string(policy_urn_str) if policy_urn_str else None
        scope = PolicyScope(target_type=scope_type, target_urn=scope_urn) if scope_type else None
        
        rules = []
        for r in rules_data:
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
            
        policy = CompliancePolicy(
            row_id=str(row_id),
            policy_id=str(policy_id),
            policy_urn=urn,
            priority=priority,
            scope=scope,
            signature_block=sig_data,
            created_at=created_at.replace(tzinfo=timezone.utc),
            updated_at=updated_at.replace(tzinfo=timezone.utc)
        )
        object.__setattr__(policy, "state", PolicyLifecycleState(state_str))
        object.__setattr__(policy, "rules", ImmutableList(rules, policy, "rules"))
        return policy

class PostgresAuthorizationPolicyRepository(AuthorizationPolicyRepository):
    def __init__(self, conn):
        self.conn = conn

    def save(self, policy: AuthorizationPolicy) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO authorization_policies (
                    policy_id, policy_urn, state, roles_mapping, created_at
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    policy.policy_id,
                    policy.policy_urn,
                    policy.state,
                    json.dumps(policy.roles_mapping),
                    policy.created_at
                )
            )

    def find_by_id(self, policy_id: str) -> Optional[AuthorizationPolicy]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT policy_id, policy_urn, state, roles_mapping, created_at
                FROM authorization_policies
                WHERE policy_id = %s
                """,
                (policy_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_entity(row)

    def find_by_urn(self, urn_str: str) -> Optional[AuthorizationPolicy]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT policy_id, policy_urn, state, roles_mapping, created_at
                FROM authorization_policies
                WHERE policy_urn = %s
                """,
                (urn_str,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_entity(row)

    def find_active_policy(self) -> Optional[AuthorizationPolicy]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT policy_id, policy_urn, state, roles_mapping, created_at
                FROM authorization_policies
                WHERE state = 'ACTIVE'
                ORDER BY created_at DESC LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_entity(row)

    def _row_to_entity(self, row) -> AuthorizationPolicy:
        policy_id, policy_urn, state, roles_mapping, created_at = row
        return AuthorizationPolicy(
            policy_id=str(policy_id),
            policy_urn=policy_urn,
            state=state,
            roles_mapping=roles_mapping,
            created_at=created_at.replace(tzinfo=timezone.utc)
        )

class PostgresExceptionTokenRepository(ExceptionTokenRepository):
    def __init__(self, conn):
        self.conn = conn

    def save(self, token: ExceptionToken) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO exception_tokens (
                    token_hash, token_urn, order_id, state, target_type, target_urn, limit_parameter, limit_ceiling, start_time, expire_time, cio_signature, compliance_signature, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    token.token_hash,
                    token.token_urn,
                    token.order_id,
                    token.state,
                    token.target_type,
                    token.target_urn,
                    token.limit_parameter,
                    token.limit_ceiling,
                    token.start_time,
                    token.expire_time,
                    token.cio_signature,
                    token.compliance_signature,
                    token.created_at
                )
            )

    def find_by_hash(self, token_hash: str) -> Optional[ExceptionToken]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT token_hash, token_urn, order_id, state, target_type, target_urn, limit_parameter, limit_ceiling, start_time, expire_time, cio_signature, compliance_signature, created_at
                FROM exception_tokens
                WHERE token_hash = %s
                """,
                (token_hash,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_entity(row)

    def find_active_by_order_id(self, order_id: str) -> Optional[ExceptionToken]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT token_hash, token_urn, order_id, state, target_type, target_urn, limit_parameter, limit_ceiling, start_time, expire_time, cio_signature, compliance_signature, created_at
                FROM exception_tokens
                WHERE order_id = %s AND state = 'ACTIVE'
                ORDER BY created_at DESC LIMIT 1
                """,
                (order_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_entity(row)

    def _row_to_entity(self, row) -> ExceptionToken:
        token_hash, token_urn, order_id, state, target_type, target_urn, limit_parameter, limit_ceiling, start_time, expire_time, cio_signature, compliance_signature, created_at = row
        return ExceptionToken(
            token_hash=token_hash,
            token_urn=token_urn,
            order_id=order_id,
            state=state,
            target_type=target_type,
            target_urn=target_urn,
            limit_parameter=limit_parameter,
            limit_ceiling=float(limit_ceiling),
            start_time=start_time.replace(tzinfo=timezone.utc),
            expire_time=expire_time.replace(tzinfo=timezone.utc),
            cio_signature=cio_signature,
            compliance_signature=compliance_signature,
            created_at=created_at.replace(tzinfo=timezone.utc)
        )

class PostgresExceptionRevocationRepository(ExceptionRevocationRepository):
    def __init__(self, conn):
        self.conn = conn

    def save(self, revocation: ExceptionRevocation) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO exception_revocations (
                    revocation_id, token_hash, revoked_by, revoked_at, reason
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    revocation.revocation_id,
                    revocation.token_hash,
                    revocation.revoked_by,
                    revocation.revoked_at,
                    revocation.reason
                )
            )

    def find_by_token_hash(self, token_hash: str) -> Optional[ExceptionRevocation]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT revocation_id, token_hash, revoked_by, revoked_at, reason
                FROM exception_revocations
                WHERE token_hash = %s
                """,
                (token_hash,)
            )
            row = cur.fetchone()
            if not row:
                return None
            revocation_id, token_hash, revoked_by, revoked_at, reason = row
            return ExceptionRevocation(
                revocation_id=str(revocation_id),
                token_hash=token_hash,
                revoked_by=revoked_by,
                revoked_at=revoked_at.replace(tzinfo=timezone.utc),
                reason=reason
            )

class PostgresGovernanceDecisionRecordRepository(GovernanceDecisionRecordRepository):
    def __init__(self, conn):
        self.conn = conn

    def save(self, record: GovernanceDecisionRecord) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO governance_decision_records (
                    decision_id, order_id, decision_outcome, policy_version_urn, exception_token_urn, portfolio_snapshot_id, risk_evaluation_id, evaluated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    record.decision_id,
                    record.order_id,
                    record.decision_outcome,
                    record.policy_version_urn,
                    record.exception_token_urn,
                    record.portfolio_snapshot_id,
                    record.risk_evaluation_id,
                    record.evaluated_at
                )
            )

    def find_by_id(self, decision_id: str) -> Optional[GovernanceDecisionRecord]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT decision_id, order_id, decision_outcome, policy_version_urn, exception_token_urn, portfolio_snapshot_id, risk_evaluation_id, evaluated_at
                FROM governance_decision_records
                WHERE decision_id = %s
                """,
                (decision_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            decision_id, order_id, decision_outcome, policy_version_urn, exception_token_urn, portfolio_snapshot_id, risk_evaluation_id, evaluated_at = row
            return GovernanceDecisionRecord(
                decision_id=str(decision_id),
                order_id=order_id,
                decision_outcome=decision_outcome,
                policy_version_urn=policy_version_urn,
                exception_token_urn=exception_token_urn,
                portfolio_snapshot_id=portfolio_snapshot_id,
                risk_evaluation_id=risk_evaluation_id,
                evaluated_at=evaluated_at.replace(tzinfo=timezone.utc)
            )

PostgresGovernanceDecisionRepository = PostgresGovernanceDecisionRecordRepository

class PostgresRiskStateSnapshotRepository(RiskStateSnapshotRepository):
    def __init__(self, conn):
        self.conn = conn

    def save(self, snapshot: RiskStateSnapshot) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO risk_state_snapshots (
                    portfolio_snapshot_id, risk_metrics, concentration_stats, evaluated_at, cached_at
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (portfolio_snapshot_id) DO UPDATE SET
                    risk_metrics = EXCLUDED.risk_metrics,
                    concentration_stats = EXCLUDED.concentration_stats,
                    evaluated_at = EXCLUDED.evaluated_at,
                    cached_at = EXCLUDED.cached_at
                """,
                (
                    snapshot.portfolio_snapshot_id,
                    json.dumps(snapshot.risk_metrics),
                    json.dumps(snapshot.concentration_stats),
                    snapshot.evaluated_at,
                    snapshot.cached_at
                )
            )

    def find_by_snapshot_id(self, portfolio_snapshot_id: str) -> Optional[RiskStateSnapshot]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT portfolio_snapshot_id, risk_metrics, concentration_stats, evaluated_at, cached_at
                FROM risk_state_snapshots
                WHERE portfolio_snapshot_id = %s
                """,
                (portfolio_snapshot_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            portfolio_snapshot_id, risk_metrics, concentration_stats, evaluated_at, cached_at = row
            return RiskStateSnapshot(
                portfolio_snapshot_id=portfolio_snapshot_id,
                risk_metrics=risk_metrics,
                concentration_stats=concentration_stats,
                evaluated_at=evaluated_at.replace(tzinfo=timezone.utc),
                cached_at=cached_at.replace(tzinfo=timezone.utc)
            )
