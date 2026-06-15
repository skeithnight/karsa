import os
import json
import base64
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from cryptography.hazmat.primitives.asymmetric import ed25519
from karsa.shared.infrastructure.uow import ConcurrencyConflictError

from karsa.governance.domain.models import (
    PolicyURN, PolicyScope, PolicyCondition, PolicyRule, PolicyAction,
    CompliancePolicy, AuthorizationPolicy, ExceptionToken, ExceptionRevocation,
    GovernanceDecisionRecord, RiskStateSnapshot, GovernanceBudgetCache,
    GovernanceAuditChain, PolicyLifecycleState, ImmutableList
)
from karsa.domain.models import WorkflowState
from karsa.governance.infrastructure.repositories import (
    InMemoryCompliancePolicyRepository, InMemoryAuthorizationPolicyRepository,
    InMemoryExceptionTokenRepository, InMemoryExceptionRevocationRepository,
    InMemoryGovernanceDecisionRecordRepository, InMemoryGovernanceAuditRepository,
    InMemoryGovernanceBudgetCacheRepository, FileCompliancePolicyRepository,
    FileGovernanceDecisionRecordRepository,
    FileGovernanceAuditRepository, FileGovernanceBudgetCacheRepository,
    serialize_compliance_policy, serialize_governance_audit_chain,
    InMemoryRiskStateSnapshotRepository
)
from karsa.governance.application.services import (
    PolicyRegistryService, ExceptionService, PolicyEvaluationService,
    GovernanceAuditService, verify_signature
)
from karsa.governance.config import ConfigurationLoader
from karsa.governance.evaluator import GovernanceEvaluator
from karsa.governance.projection import GovernanceDecisionRepository as LegacyDecisionRepository

@pytest.fixture
def event_bus():
    events = []
    def publish(event):
        events.append(event)
    return publish, events

# Helper to generate Ed25519 key pair
def generate_keys():
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    pub_hex = public_key.public_bytes_raw().hex()
    return private_key, pub_hex

def sign_payload(private_key, payload: str) -> str:
    signature = private_key.sign(payload.encode("utf-8"))
    return base64.b64encode(signature).decode("utf-8")

# === 1. Cryptographic helper verify_signature tests ===
def test_verify_signature_edge_cases():
    private_key, pub_hex = generate_keys()
    payload = "TEST_PAYLOAD"
    signature = sign_payload(private_key, payload)

    # Valid signature
    assert verify_signature(pub_hex, payload, signature) is True
    # Invalid payload
    assert verify_signature(pub_hex, "WRONG_PAYLOAD", signature) is False
    # Malformed public key hex
    assert verify_signature("invalid_hex", payload, signature) is False
    # Malformed base64 signature
    assert verify_signature(pub_hex, payload, "invalid_b64!!!") is False


# === 2. PolicyRegistryService tests ===
def test_policy_registration_failures():
    policy_repo = InMemoryCompliancePolicyRepository()
    registry = PolicyRegistryService(policy_repo)

    scope = PolicyScope("CAPABILITY", "urn:karsa:capability:chat:v1")
    rules = [PolicyRule(action=PolicyAction.DENY)]
    
    registry.register_policy(
        policy_id="pol-1",
        urn_str="urn:karsa:policy:budget:max_cost:1.0.0",
        priority=100,
        scope=scope,
        rules=rules
    )

    # Duplicate policy ID
    with pytest.raises(ValueError, match="already exists"):
        registry.register_policy(
            policy_id="pol-1",
            urn_str="urn:karsa:policy:budget:different:1.0.0",
            priority=100,
            scope=scope,
            rules=rules
        )

    # Duplicate URN
    with pytest.raises(ValueError, match="already exists"):
        registry.register_policy(
            policy_id="pol-2",
            urn_str="urn:karsa:policy:budget:max_cost:1.0.0",
            priority=100,
            scope=scope,
            rules=rules
        )

def test_policy_transition_validation(event_bus):
    policy_repo = InMemoryCompliancePolicyRepository()
    auth_repo = InMemoryAuthorizationPolicyRepository()
    publish, events = event_bus
    registry = PolicyRegistryService(policy_repo, auth_repo, event_publisher=publish)

    scope = PolicyScope("CAPABILITY", "urn:karsa:capability:chat:v1")
    rules = [PolicyRule(action=PolicyAction.DENY)]
    registry.register_policy("pol-1", "urn:karsa:policy:budget:max_cost:1.0.0", 100, scope, rules)

    # Transition to non-existent policy
    with pytest.raises(ValueError, match="not found"):
        registry.transition_policy_state("non-existent", PolicyLifecycleState.REVIEW)

    # APPROVED requires signature block
    with pytest.raises(ValueError, match="Signature block is required"):
        registry.transition_policy_state("pol-1", PolicyLifecycleState.REVIEW)
        registry.transition_policy_state("pol-1", PolicyLifecycleState.APPROVED)

    # APPROVED with missing AuthorizationPolicy
    with pytest.raises(ValueError, match="No active AuthorizationPolicy registered"):
        registry.transition_policy_state("pol-1", PolicyLifecycleState.APPROVED, signature_block={"cio": "sig"})

    # Setup active AuthPolicy
    cio_priv, cio_pub = generate_keys()
    comp_priv, comp_pub = generate_keys()
    auth_policy = AuthorizationPolicy(
        policy_id="auth-1",
        policy_urn="urn:karsa:auth-policy:standard:1.0.0",
        state="ACTIVE",
        roles_mapping=[
            {"role": "CIO", "public_key_hex": cio_pub},
            {"role": "COMPLIANCE_OFFICER", "public_key_hex": comp_pub}
        ]
    )
    auth_repo.save(auth_policy)

    # Signature payload logic: APPROVE:<policy_urn_str>
    payload = "APPROVE:urn:karsa:policy:budget:max_cost:1.0.0"
    valid_cio_sig = sign_payload(cio_priv, payload)
    valid_comp_sig = sign_payload(comp_priv, payload)

    # Invalid CIO signature
    sig_block = {"cio_signature": "bad_sig", "compliance_signature": valid_comp_sig}
    with pytest.raises(ValueError, match="Invalid CIO approval signature"):
        registry.transition_policy_state("pol-1", PolicyLifecycleState.APPROVED, signature_block=sig_block)

    # Invalid Compliance signature
    sig_block = {"cio_signature": valid_cio_sig, "compliance_signature": "bad_sig"}
    with pytest.raises(ValueError, match="Invalid Compliance Officer approval signature"):
        registry.transition_policy_state("pol-1", PolicyLifecycleState.APPROVED, signature_block=sig_block)

    # Valid signatures approval
    sig_block = {"cio_signature": valid_cio_sig, "compliance_signature": valid_comp_sig}
    registry.transition_policy_state("pol-1", PolicyLifecycleState.APPROVED, signature_block=sig_block)
    policy = policy_repo.find_by_id("pol-1")
    assert policy.state == PolicyLifecycleState.APPROVED

    # Setup a prior active policy to test retirement on new active transition
    # We temporarily pop pol-1 from the repository dict to ensure pol-prior is evaluated first
    pol1_data = policy_repo._data.pop("pol-1")
    prior_active = CompliancePolicy(
        policy_id="pol-prior",
        policy_urn=PolicyURN.from_string("urn:karsa:policy:budget:max_cost:1.0.0"),
        state=PolicyLifecycleState.ACTIVE
    )
    policy_repo.save(prior_active)
    policy_repo._data["pol-1"] = pol1_data

    # Transition from APPROVED to ACTIVE
    registry.transition_policy_state("pol-1", PolicyLifecycleState.ACTIVE)
    
    # Prior policy should be retired
    retired = policy_repo.find_by_id("pol-prior")
    assert retired.state == PolicyLifecycleState.RETIRED


# === 3. ExceptionService tests ===
def test_exception_service_flows():
    token_repo = InMemoryExceptionTokenRepository()
    revocation_repo = InMemoryExceptionRevocationRepository()
    auth_repo = InMemoryAuthorizationPolicyRepository()
    service = ExceptionService(token_repo, revocation_repo, auth_repo)

    cio_priv, cio_pub = generate_keys()
    comp_priv, comp_pub = generate_keys()
    
    token = ExceptionToken(
        token_hash="tokenhash123",
        token_urn="urn:karsa:exception:tokenhash123",
        order_id="order-1",
        state="REQUESTED",
        target_type="PORTFOLIO",
        target_urn="urn:karsa:portfolio:1",
        limit_parameter="portfolio_var_95",
        limit_ceiling=0.08,
        start_time=datetime.now(timezone.utc) - timedelta(hours=1),
        expire_time=datetime.now(timezone.utc) + timedelta(hours=1)
    )

    # Grant exception with missing AuthPolicy
    with pytest.raises(ValueError, match="No active AuthorizationPolicy registered"):
        service.grant_exception(token)

    auth_policy = AuthorizationPolicy(
        policy_id="auth-1",
        policy_urn="urn:karsa:auth-policy:standard:1.0.0",
        state="ACTIVE",
        roles_mapping=[
            {"role": "CIO", "public_key_hex": cio_pub},
            {"role": "COMPLIANCE_OFFICER", "public_key_hex": comp_pub}
        ]
    )
    auth_repo.save(auth_policy)

    payload_dict = {
        "order_id": token.order_id,
        "target_type": token.target_type,
        "target_urn": token.target_urn,
        "limit_parameter": token.limit_parameter,
        "limit_ceiling": token.limit_ceiling,
        "start_time": token.start_time.isoformat(),
        "expire_time": token.expire_time.isoformat()
    }
    canonical_payload = json.dumps(payload_dict, sort_keys=True)
    cio_sig = sign_payload(cio_priv, canonical_payload)
    comp_sig = sign_payload(comp_priv, canonical_payload)

    # Invalid signature grant
    token.cio_signature = "bad"
    token.compliance_signature = comp_sig
    with pytest.raises(ValueError, match="Invalid CIO signature"):
        service.grant_exception(token)

    token.cio_signature = cio_sig
    token.compliance_signature = "bad"
    with pytest.raises(ValueError, match="Invalid Compliance Officer signature"):
        service.grant_exception(token)

    # Valid signatures grant
    token.cio_signature = cio_sig
    token.compliance_signature = comp_sig
    service.grant_exception(token)
    assert token_repo.find_by_hash("tokenhash123").state == "ACTIVE"

    # Revocation of non-existent token
    with pytest.raises(ValueError, match="not found"):
        service.revoke_exception("non-existent-hash", "cio", "emergency")

    # Valid revocation
    service.revoke_exception("tokenhash123", "cio", "emergency")
    assert token_repo.find_by_hash("tokenhash123").state == "REVOKED"
    assert revocation_repo.find_by_token_hash("tokenhash123") is not None

    # Double revocation block
    with pytest.raises(ValueError, match="already revoked"):
        service.revoke_exception("tokenhash123", "cio", "emergency")


# === 4. PolicyEvaluationService (PDP) tests ===
def test_pdp_evaluation_logic():
    policy_repo = InMemoryCompliancePolicyRepository()
    cache_repo = InMemoryGovernanceBudgetCacheRepository()
    decision_repo = InMemoryGovernanceDecisionRecordRepository()
    token_repo = InMemoryExceptionTokenRepository()
    revocation_repo = InMemoryExceptionRevocationRepository()
    
    eval_service = PolicyEvaluationService(
        policy_repo=policy_repo,
        snapshot_repo=cache_repo,
        decision_repo=decision_repo,
        token_repo=token_repo,
        revocation_repo=revocation_repo
    )

    # Emergency Override
    dec_override = eval_service.check_execution_authorization(
        execution_id="exec-override",
        capability_urn="urn:karsa:capability:chat:v1",
        context={},
        override_token="admin-override-token-123"
    )
    assert dec_override.decision_outcome == "ALLOW"
    
    # Invalid Emergency Override
    with pytest.raises(ValueError, match="Invalid emergency override token"):
        eval_service.check_execution_authorization(
            execution_id="exec-override",
            capability_urn="urn:karsa:capability:chat:v1",
            context={},
            override_token="bad-token"
        )

    # Replay Determinism Bypass missing historical decision
    with pytest.raises(ValueError, match="historical_decision must be provided"):
        eval_service.check_execution_authorization(
            execution_id="exec-replay",
            capability_urn="urn:karsa:capability:chat:v1",
            context={},
            replay_mode=True
        )

    # Stale budget cache
    cache = GovernanceBudgetCache(workflow_id="wf-stale", remaining_budget=100.0)
    cache.last_updated_at = datetime.now(timezone.utc) - timedelta(seconds=70)
    cache_repo.save(cache)
    with pytest.raises(Exception, match="StaleBudgetSnapshotError"):
        eval_service.check_execution_authorization(
            execution_id="exec-stale",
            capability_urn="urn:karsa:capability:chat:v1",
            context={"workflow_id": "wf-stale", "estimated_cost": 10.0}
        )

    # Budget Exceeded
    cache_ok = GovernanceBudgetCache(workflow_id="wf-ok", remaining_budget=5.0)
    cache_repo.save(cache_ok)
    dec_deny = eval_service.check_execution_authorization(
        execution_id="exec-deny",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"workflow_id": "wf-ok", "estimated_cost": 10.0}
    )
    assert dec_deny.decision_outcome == "DENY"

    # Stale risk snapshot
    risk_repo = InMemoryCompliancePolicyRepository() # Mock snapshot repo
    eval_service.snapshot_repo = risk_repo
    
    stale_snap = RiskStateSnapshot(
        portfolio_snapshot_id="snap-stale",
        risk_metrics={"var_95": 0.04},
        concentration_stats={"hhi": 0.2},
        evaluated_at=datetime.now(timezone.utc) - timedelta(seconds=700)
    )
    object.__setattr__(risk_repo, "find_by_snapshot_id", lambda sid: stale_snap)
    
    dec_stale_snap = eval_service.check_execution_authorization(
        execution_id="exec-stale-snap",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"portfolio_snapshot_id": "snap-stale"}
    )
    assert dec_stale_snap.decision_outcome == "DENY"
    assert dec_stale_snap.reason == "StaleRiskSnapshot"

    # Active Policy matches check
    active_policy = CompliancePolicy(
        policy_id="pol-limits",
        policy_urn=PolicyURN.from_string("urn:karsa:policy:limit:standard:1.0.0"),
        state=PolicyLifecycleState.ACTIVE,
        priority=50,
        scope=PolicyScope("CAPABILITY", "urn:karsa:capability:chat:v1"),
        rules=[
            PolicyRule(
                condition=PolicyCondition("portfolio_var_95", "GREATER_THAN", "0.05"),
                action=PolicyAction.DENY,
                priority=10
            )
        ]
    )
    policy_repo.save(active_policy)

    # Snapshot OK
    ok_snap = RiskStateSnapshot(
        portfolio_snapshot_id="snap-ok",
        risk_metrics={"var_95": 0.03},
        concentration_stats={"hhi": 0.1},
        evaluated_at=datetime.now(timezone.utc)
    )
    object.__setattr__(risk_repo, "find_by_snapshot_id", lambda sid: ok_snap)
    
    dec_allow = eval_service.check_execution_authorization(
        execution_id="exec-ok",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"portfolio_snapshot_id": "snap-ok"}
    )
    assert dec_allow.decision_outcome == "ALLOW"

    # Limit Breached and Denied
    breached_snap = RiskStateSnapshot(
        portfolio_snapshot_id="snap-breach",
        risk_metrics={"var_95": 0.06},
        concentration_stats={"hhi": 0.1},
        evaluated_at=datetime.now(timezone.utc)
    )
    object.__setattr__(risk_repo, "find_by_snapshot_id", lambda sid: breached_snap)
    
    dec_breach = eval_service.check_execution_authorization(
        execution_id="exec-breach",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"portfolio_snapshot_id": "snap-breach"}
    )
    assert dec_breach.decision_outcome == "DENY"

    # Exception Token overrides breached limit
    token = ExceptionToken(
        token_hash="exception-token-hash",
        token_urn="urn:karsa:exception:exception-token-hash",
        order_id="exec-override-breach",
        state="ACTIVE",
        target_type="PORTFOLIO",
        target_urn="urn:karsa:portfolio:1",
        limit_parameter="portfolio_var_95",
        limit_ceiling=0.08,
        start_time=datetime.now(timezone.utc) - timedelta(hours=1),
        expire_time=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    token_repo.save(token)

    dec_exception = eval_service.check_execution_authorization(
        execution_id="exec-override-breach",
        capability_urn="urn:karsa:capability:chat:v1",
        context={
            "portfolio_snapshot_id": "snap-breach",
            "exception_token_urn": "urn:karsa:exception:exception-token-hash"
        }
    )
    assert dec_exception.decision_outcome == "ALLOW_VIA_EXCEPTION"


# === 5. Domain Models edge cases ===
def test_policy_urn_parsing_failures():
    with pytest.raises(ValueError, match="Invalid policy URN prefix"):
        PolicyURN.from_string("urn:bad:prefix:1.0")
    with pytest.raises(ValueError, match="Invalid policy URN format"):
        PolicyURN.from_string("urn:karsa:policy:short")
    with pytest.raises(ValueError, match="components cannot be empty"):
        PolicyURN.from_string("urn:karsa:policy:ns::v1")

def test_policy_condition_evaluation_failures():
    # Value parsing error
    cond = PolicyCondition("portfolio_var_95", "GREATER_THAN", "invalid_float")
    assert cond.evaluate({"portfolio_var_95": 0.05}) is False

    # Attribute not in context
    cond2 = PolicyCondition("missing_attr", "GREATER_THAN", "5.0")
    assert cond2.evaluate({"other_attr": 6.0}) is False

    # Operator unsupported fallback
    cond3 = PolicyCondition("portfolio_var_95", "UNSUPPORTED_OP", "0.05")
    assert cond3.evaluate({"portfolio_var_95": 0.06}) is False

def test_immutable_list_exceptions():
    policy = CompliancePolicy()
    policy.rules = [PolicyRule()]
    object.__setattr__(policy, "state", PolicyLifecycleState.ACTIVE)

    # Rules are wrapped in ImmutableList
    with pytest.raises(ValueError, match="Cannot modify policy definition"):
        policy.rules.append(PolicyRule())
    with pytest.raises(ValueError, match="Cannot modify policy definition"):
        policy.rules.extend([PolicyRule()])
    with pytest.raises(ValueError, match="Cannot modify policy definition"):
        policy.rules.insert(0, PolicyRule())
    with pytest.raises(ValueError, match="Cannot modify policy definition"):
        policy.rules.pop()
    with pytest.raises(ValueError, match="Cannot modify policy definition"):
        policy.rules.clear()
    with pytest.raises(ValueError, match="Cannot modify policy definition"):
        del policy.rules[0]

def test_staleness_methods():
    snap = RiskStateSnapshot(
        portfolio_snapshot_id="s1",
        evaluated_at=datetime.now(timezone.utc) - timedelta(seconds=601)
    )
    assert snap.is_stale(600) is True

    budget = GovernanceBudgetCache(
        workflow_id="w1",
        remaining_budget=10.0,
        last_updated_at=datetime.now(timezone.utc) - timedelta(seconds=61)
    )
    assert budget.is_stale(60) is True


# === 6. File Repositories edge cases ===
def test_file_repositories_concurrency_conflict(tmp_path):
    policy_repo = FileCompliancePolicyRepository(tmp_path)
    policy = CompliancePolicy(
        policy_id="pol-1",
        policy_urn=PolicyURN("budget", "cost_limit", "1.0.0"),
        state=PolicyLifecycleState.DRAFT
    )
    policy_repo.save(policy)

    # Mutate aggregate version to trigger ConcurrencyConflictError
    loaded = policy_repo.find_by_id("pol-1")
    loaded.transition_to(PolicyLifecycleState.REVIEW)
    policy_repo.save(loaded) # version becomes 1 in file

    with pytest.raises(ConcurrencyConflictError):
        policy_repo.save(policy) # policy in memory has version 0

def test_file_audit_repo_concurrency_conflict(tmp_path):
    audit_repo = FileGovernanceAuditRepository(tmp_path)
    chain = GovernanceAuditChain(
        audit_id="audit-1",
        decision_id="dec-1",
        previous_hash="",
        current_hash="hash"
    )
    audit_repo.append_chain(chain)

    loaded = audit_repo.get_latest_entry()
    loaded.increment_version()
    audit_repo.append_chain(loaded) # version becomes 1 in file

    with pytest.raises(ConcurrencyConflictError):
        audit_repo.append_chain(chain) # chain in memory has version 0

def test_file_repos_missing_and_corrupt_files(tmp_path):
    policy_repo = FileCompliancePolicyRepository(tmp_path)
    assert policy_repo.find_by_id("missing") is None
    assert policy_repo.find_latest_by_urn(PolicyURN("b", "c", "1")) is None
    assert policy_repo.find_active_for_scope("CAPABILITY", "urn") == []

    decision_repo = FileGovernanceDecisionRecordRepository(tmp_path)
    assert decision_repo.find_by_id("missing") is None

    audit_repo = FileGovernanceAuditRepository(tmp_path)
    assert audit_repo.get_latest_entry() is None

    budget_repo = FileGovernanceBudgetCacheRepository(tmp_path)
    assert budget_repo.find_by_workflow_id("missing") is None


# === 7. ConfigurationLoader TOML parsing ===
def test_config_loader_toml_parsing(tmp_path):
    toml_file = tmp_path / "karsa.toml"
    with open(toml_file, "w") as f:
        f.write("""
        # Comments should be ignored
        [limits]
        max_workflow_cost = 12.5
        max_workflow_tokens = 5000
        max_review_cycles = 5
        max_cycle_cost = 3.2
        string_limit = "unlimited"
        invalid_line_without_equals
        """)

    loader = ConfigurationLoader(toml_file)
    policy = loader.load_policy()
    assert policy.max_workflow_cost == 12.5
    assert policy.max_workflow_tokens == 5000
    assert policy.max_review_cycles == 5
    assert policy.max_cycle_cost == 3.2

    # Non-existent file fallback
    loader_missing = ConfigurationLoader(tmp_path / "missing.toml")
    p_default = loader_missing.load_policy()
    assert p_default.max_workflow_cost == 0.0

    # Snapshot validation
    snap = loader.create_snapshot("2.0")
    assert snap.policy_version == "2.0"
    assert snap.max_workflow_cost == 12.5
    assert len(snap.policy_hash) == 64 # SHA-256 string length


# === 8. Legacy GovernanceEvaluator and DecisionRepository ===
def test_legacy_evaluator_limits():
    evaluator = GovernanceEvaluator()
    from karsa.domain.models import WorkflowSnapshot, GovernancePolicySnapshot
    
    # Missing policy snapshot
    snap_no_policy = WorkflowSnapshot("w-1", WorkflowState.IDEA, policy=None)
    dec = evaluator.evaluate(snap_no_policy, "e1", "r1")
    assert dec.decision_type == "ALLOW"

    policy_snap = GovernancePolicySnapshot(
        policy_version="1.0",
        policy_hash="hash",
        max_workflow_cost=10.0,
        max_workflow_tokens=1000,
        max_review_cycles=3,
        max_cycle_cost=4.0
    )

    # Under limits
    snap_ok = WorkflowSnapshot(
        workflow_id="w-1",
        state=WorkflowState.IDEA,
        policy=policy_snap,
        data={"metrics": {"total_cost": 5.0, "total_tokens": 500, "execution_count": 1}, "review": {"review_cycle_metrics": {"total_cost": 2.0}}},
        last_sequence_number=1
    )
    dec_ok = evaluator.evaluate(snap_ok, "e1", "r1")
    assert dec_ok.decision_type == "ALLOW"

    # Breaches
    # 1. Total Cost
    snap_cost = WorkflowSnapshot("w-1", WorkflowState.IDEA, policy=policy_snap, data={"metrics": {"total_cost": 15.0}}, last_sequence_number=1)
    assert evaluator.evaluate(snap_cost, "e1", "r1").decision_type == "DENY"

    # 2. Total Tokens
    snap_tokens = WorkflowSnapshot("w-1", WorkflowState.IDEA, policy=policy_snap, data={"metrics": {"total_tokens": 1500}}, last_sequence_number=1)
    assert evaluator.evaluate(snap_tokens, "e1", "r1").decision_type == "DENY"

    # 3. Execulations (Review Cycles)
    snap_cycles = WorkflowSnapshot("w-1", WorkflowState.IDEA, policy=policy_snap, data={"metrics": {"execution_count": 4}}, last_sequence_number=1)
    assert evaluator.evaluate(snap_cycles, "e1", "r1").decision_type == "DENY"

    # 4. Cycle Cost
    snap_cycle_cost = WorkflowSnapshot("w-1", WorkflowState.IDEA, policy=policy_snap, data={"review": {"review_cycle_metrics": {"total_cost": 5.0}}}, last_sequence_number=1)
    assert evaluator.evaluate(snap_cycle_cost, "e1", "r1").decision_type == "DENY"

def test_legacy_decision_repository():
    from karsa.domain.persistence import EventJournalRepository
    from karsa.domain.events import GovernanceDecisionEvent
    from karsa.domain.models import GovernanceDecision
    
    event_repo = InMemoryGovernanceAuditRepository() # Dummy repo object
    object.__setattr__(event_repo, "load", lambda wid: [
        GovernanceDecisionEvent(decision=GovernanceDecision("w1", "r1", "e1", 1, "ALLOW", "OK"), sequence_number=1),
        "not_decision_event"
    ])
    
    repo = LegacyDecisionRepository(event_repo)
    decisions = repo.get_decisions("w1")
    assert len(decisions) == 1
    assert decisions[0].workflow_id == "w1"

def test_registry_retired_transition_and_missing_keys(event_bus):
    policy_repo = InMemoryCompliancePolicyRepository()
    auth_repo = InMemoryAuthorizationPolicyRepository()
    publish, events = event_bus
    registry = PolicyRegistryService(policy_repo, auth_repo, event_publisher=publish)
    
    scope = PolicyScope("CAPABILITY", "urn:karsa:capability:chat:v1")
    rules = [PolicyRule(action=PolicyAction.DENY)]
    policy = registry.register_policy("pol-ret", "urn:karsa:policy:budget:retire:1.0.0", 100, scope, rules)
    
    # Transition to REVIEW
    registry.transition_policy_state("pol-ret", PolicyLifecycleState.REVIEW)
    # Transition to RETIRED from REVIEW
    registry.transition_policy_state("pol-ret", PolicyLifecycleState.RETIRED)
    assert policy_repo.find_by_id("pol-ret").state == PolicyLifecycleState.RETIRED
    
    # Missing CIO / Compliance keys in AuthPolicy for approval
    auth_policy_empty = AuthorizationPolicy(
        policy_id="auth-empty",
        policy_urn="urn:karsa:auth-policy:empty:1.0.0",
        state="ACTIVE",
        roles_mapping=[]
    )
    auth_repo.save(auth_policy_empty)
    
    policy2 = registry.register_policy("pol-ret2", "urn:karsa:policy:budget:retire2:1.0.0", 100, scope, rules)
    registry.transition_policy_state("pol-ret2", PolicyLifecycleState.REVIEW)
    with pytest.raises(ValueError, match="CIO and Compliance keys not configured"):
        registry.transition_policy_state("pol-ret2", PolicyLifecycleState.APPROVED, signature_block={"cio_signature": "sig", "compliance_signature": "sig"})

def test_exception_service_event_publisher_and_missing_keys(event_bus):
    token_repo = InMemoryExceptionTokenRepository()
    revocation_repo = InMemoryExceptionRevocationRepository()
    auth_repo = InMemoryAuthorizationPolicyRepository()
    publish, events = event_bus
    service = ExceptionService(token_repo, revocation_repo, auth_repo, event_publisher=publish)
    
    auth_policy_empty = AuthorizationPolicy(
        policy_id="auth-empty",
        policy_urn="urn:karsa:auth-policy:empty:1.0.0",
        state="ACTIVE",
        roles_mapping=[]
    )
    auth_repo.save(auth_policy_empty)
    
    token = ExceptionToken(
        token_hash="tokenhash123-2",
        token_urn="urn:karsa:exception:tokenhash123-2",
        order_id="order-2",
        state="REQUESTED"
    )
    
    with pytest.raises(ValueError, match="CIO and Compliance keys not configured"):
        service.grant_exception(token)

def test_pdp_event_publisher_and_audit(event_bus):
    policy_repo = InMemoryCompliancePolicyRepository()
    cache_repo = InMemoryGovernanceBudgetCacheRepository()
    decision_repo = InMemoryGovernanceDecisionRecordRepository()
    publish, events = event_bus
    audit_repo = InMemoryGovernanceAuditRepository()
    audit_service = GovernanceAuditService(audit_repo)
    
    eval_service = PolicyEvaluationService(
        policy_repo=policy_repo,
        snapshot_repo=cache_repo,
        decision_repo=decision_repo,
        event_publisher=publish,
        audit_service=audit_service
    )
    
    # Setup cache
    cache = GovernanceBudgetCache(workflow_id="wf-1", remaining_budget=50.0)
    cache_repo.save(cache)
    
    # Active policy
    policy = CompliancePolicy(
        policy_id="p-1",
        policy_urn=PolicyURN.from_string("urn:karsa:policy:budget:cost:1.0.0"),
        state=PolicyLifecycleState.ACTIVE,
        scope=PolicyScope("CAPABILITY", "urn:karsa:capability:chat:v1")
    )
    policy_repo.save(policy)
    
    dec = eval_service.check_execution_authorization(
        execution_id="exec-1",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"workflow_id": "wf-1", "estimated_cost": 5.0, "is_execution": True}
    )
    
    # Wait for the async thread of trigger_legacy_audit to complete
    import time
    time.sleep(0.1)
    
    assert dec.decision_outcome == "ALLOW"
    assert len(events) > 0
    assert audit_repo.get_latest_entry() is not None

def test_policy_condition_more_operators():
    # EQUALS
    cond_eq = PolicyCondition("attribute", "EQUALS", "match_value")
    assert cond_eq.evaluate({"attribute": "match_value"}) is True
    assert cond_eq.evaluate({"attribute": "other_value"}) is False

    # LESS_THAN_OR_EQUAL
    cond_lte = PolicyCondition("attribute", "LESS_THAN_OR_EQUAL", "5.0")
    assert cond_lte.evaluate({"attribute": 4.0}) is True
    assert cond_lte.evaluate({"attribute": 5.0}) is True
    assert cond_lte.evaluate({"attribute": 6.0}) is False

def test_immutable_list_draft_mutations():
    policy = CompliancePolicy(state=PolicyLifecycleState.DRAFT)
    policy.rules = [PolicyRule()]
    
    # Mutating rules on DRAFT policy must succeed
    policy.rules.append(PolicyRule())
    assert len(policy.rules) == 2
    
    policy.rules.pop()
    assert len(policy.rules) == 1
    
    policy.rules.clear()
    assert len(policy.rules) == 0

def test_hash_utility_functions():
    h = ExceptionToken.generate_token_hash({"data": "value"})
    assert len(h) == 64
    
    hc = GovernanceAuditChain.calculate_hash("dec-1", "APPROVED", "prev_hash")
    assert len(hc) == 64

def test_event_publisher_none():
    policy_repo = InMemoryCompliancePolicyRepository()
    registry = PolicyRegistryService(policy_repo)
    
    scope = PolicyScope("CAPABILITY", "urn:karsa:capability:chat:v1")
    rules = [PolicyRule(action=PolicyAction.DENY)]
    policy = registry.register_policy("pol-no-pub", "urn:karsa:policy:budget:nopub:1.0.0", 100, scope, rules)
    
    # Transition to REVIEW without event publisher
    registry.transition_policy_state("pol-no-pub", PolicyLifecycleState.REVIEW)
    # Transition to APPROVED without event publisher
    registry.transition_policy_state("pol-no-pub", PolicyLifecycleState.APPROVED, signature_block={"cio_signature": "sig", "compliance_signature": "sig"})
    # Transition to ACTIVE without event publisher
    registry.transition_policy_state("pol-no-pub", PolicyLifecycleState.ACTIVE)
    # Transition to RETIRED without event publisher
    registry.transition_policy_state("pol-no-pub", PolicyLifecycleState.RETIRED)

    # Exception grant and revoke without event publisher
    token_repo = InMemoryExceptionTokenRepository()
    revocation_repo = InMemoryExceptionRevocationRepository()
    auth_repo = InMemoryAuthorizationPolicyRepository()
    service = ExceptionService(token_repo, revocation_repo, auth_repo)
    
    cio_priv, cio_pub = generate_keys()
    comp_priv, comp_pub = generate_keys()
    auth_policy = AuthorizationPolicy(
        policy_id="auth-1",
        policy_urn="urn:karsa:auth-policy:standard:1.0.0",
        state="ACTIVE",
        roles_mapping=[
            {"role": "CIO", "public_key_hex": cio_pub},
            {"role": "COMPLIANCE_OFFICER", "public_key_hex": comp_pub}
        ]
    )
    auth_repo.save(auth_policy)
    
    token = ExceptionToken(
        token_hash="tokenhash-no-pub",
        token_urn="urn:karsa:exception:tokenhash-no-pub",
        order_id="order-no-pub",
        state="REQUESTED",
        target_type="PORTFOLIO",
        target_urn="urn:karsa:portfolio:1",
        limit_parameter="portfolio_var_95",
        limit_ceiling=0.08,
        start_time=datetime.now(timezone.utc) - timedelta(hours=1),
        expire_time=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    payload_dict = {
        "order_id": token.order_id,
        "target_type": token.target_type,
        "target_urn": token.target_urn,
        "limit_parameter": token.limit_parameter,
        "limit_ceiling": token.limit_ceiling,
        "start_time": token.start_time.isoformat(),
        "expire_time": token.expire_time.isoformat()
    }
    canonical_payload = json.dumps(payload_dict, sort_keys=True)
    token.cio_signature = sign_payload(cio_priv, canonical_payload)
    token.compliance_signature = sign_payload(comp_priv, canonical_payload)
    
    service.grant_exception(token)
    service.revoke_exception("tokenhash-no-pub", "cio", "emergency")

def test_immutable_list_without_check_immutability():
    # Parent has no check_immutability method
    class DummyParent:
        pass
    dummy = DummyParent()
    lst = ImmutableList([1, 2, 3], dummy, "attr")
    lst.append(4)
    lst.extend([5])
    lst.insert(0, 0)
    lst.pop()
    lst.remove(1)
    lst.clear()

def test_staleness_false():
    snap = RiskStateSnapshot(
        portfolio_snapshot_id="s1",
        evaluated_at=datetime.now(timezone.utc) - timedelta(seconds=10)
    )
    assert snap.is_stale(600) is False

    budget = GovernanceBudgetCache(
        workflow_id="w1",
        remaining_budget=10.0,
        last_updated_at=datetime.now(timezone.utc) - timedelta(seconds=10)
    )
    assert budget.is_stale(60) is False

def test_pdp_various_branches():
    policy_repo = InMemoryCompliancePolicyRepository()
    cache_repo = InMemoryGovernanceBudgetCacheRepository()
    decision_repo = InMemoryGovernanceDecisionRecordRepository()
    
    eval_service = PolicyEvaluationService(
        policy_repo=policy_repo,
        snapshot_repo=cache_repo,
        decision_repo=decision_repo
    )
    
    # 1. Budget ok (estimated_cost <= remaining_budget)
    cache = GovernanceBudgetCache(workflow_id="wf-1", remaining_budget=10.0)
    cache_repo.save(cache)
    dec_ok = eval_service.check_execution_authorization(
        execution_id="exec-1",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"workflow_id": "wf-1", "estimated_cost": 5.0}
    )
    assert dec_ok.decision_outcome == "DENY" # Denied by default because no active policy matches capability
    
    # 2. Snapshot repo has no find_by_snapshot_id
    eval_service.snapshot_repo = object() # plain object has no find_by_snapshot_id
    dec_fallback = eval_service.check_execution_authorization(
        execution_id="exec-2",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"portfolio_snapshot_id": "snap-123"}
    )
    assert dec_fallback.decision_outcome == "DENY"

    # 3. Read-only ALLOW check (is_execution is False, so decision is NOT persisted to decision_repo)
    policy = CompliancePolicy(
        policy_id="p-1",
        policy_urn=PolicyURN.from_string("urn:karsa:policy:budget:cost:1.0.0"),
        state=PolicyLifecycleState.ACTIVE,
        scope=PolicyScope("CAPABILITY", "urn:karsa:capability:chat:v1")
    )
    policy_repo.save(policy)
    
    dec_readonly = eval_service.check_execution_authorization(
        execution_id="exec-readonly",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"is_execution": False}
    )
    assert dec_readonly.decision_outcome == "ALLOW"
    assert decision_repo.find_by_id(dec_readonly.decision_id) is None

def test_immutable_list_additional_mutations():
    class DummyParent:
        pass
    dummy = DummyParent()
    lst = ImmutableList([1, 2, 3], dummy, "attr")
    lst[0] = 10     # Calls __setitem__
    del lst[0]      # Calls __delitem__
    assert len(lst) == 2

def test_governance_decision_record_post_init_branches():
    # Case: execution_id empty, order_id set
    rec1 = GovernanceDecisionRecord(order_id="order-123")
    assert rec1.execution_id == "order-123"

    # Case: both set
    rec2 = GovernanceDecisionRecord(order_id="order-123", execution_id="exec-123")
    assert rec2.order_id == "order-123"
    assert rec2.execution_id == "exec-123"

    # Case: outcome set to APPROVED, decision_outcome empty
    rec3 = GovernanceDecisionRecord(outcome="APPROVED", decision_outcome="")
    assert rec3.decision_outcome == "ALLOW"

    # Case: outcome set to DENIED, decision_outcome empty
    rec4 = GovernanceDecisionRecord(outcome="DENIED", decision_outcome="")
    assert rec4.decision_outcome == "DENY"

    # Case: outcome set to other, decision_outcome empty
    rec5 = GovernanceDecisionRecord(outcome="OTHER", decision_outcome="")
    assert rec5.decision_outcome == ""

def test_services_event_publisher_none_and_other_branches():
    # 1. ExceptionService event_publisher = None
    token_repo = InMemoryExceptionTokenRepository()
    revocation_repo = InMemoryExceptionRevocationRepository()
    auth_repo = InMemoryAuthorizationPolicyRepository()
    
    cio_priv, cio_pub = generate_keys()
    comp_priv, comp_pub = generate_keys()
    
    # Setup active AuthorizationPolicy with an extra role mapping that is not CIO/Compliance to cover loop continuation (line 214->211)
    auth_p = AuthorizationPolicy(
        policy_id="auth-1",
        policy_urn="urn:auth-1",
        state="ACTIVE",
        roles_mapping=[
            {"role": "CIO", "public_key_hex": cio_pub},
            {"role": "OTHER_ROLE", "public_key_hex": "otherkey"},
            {"role": "COMPLIANCE_OFFICER", "public_key_hex": comp_pub}
        ]
    )
    auth_repo.save(auth_p)
    
    # Create exception token
    token = ExceptionToken(
        token_hash="tokenhash",
        token_urn="urn:karsa:exception:tokenhash",
        order_id="order-1",
        state="DRAFT",
        target_type="PORTFOLIO",
        target_urn="urn:karsa:portfolio:1",
        limit_parameter="portfolio_var_95",
        limit_ceiling=0.08,
        start_time=datetime.now(timezone.utc) - timedelta(hours=1),
        expire_time=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    
    payload_dict = {
        "order_id": token.order_id,
        "target_type": token.target_type,
        "target_urn": token.target_urn,
        "limit_parameter": token.limit_parameter,
        "limit_ceiling": token.limit_ceiling,
        "start_time": token.start_time.isoformat(),
        "expire_time": token.expire_time.isoformat()
    }
    canonical_payload = json.dumps(payload_dict, sort_keys=True)
    token.cio_signature = sign_payload(cio_priv, canonical_payload)
    token.compliance_signature = sign_payload(comp_priv, canonical_payload)
    
    # Service with event_publisher = None
    service = ExceptionService(
        token_repo=token_repo,
        revocation_repo=revocation_repo,
        auth_repo=auth_repo,
        event_publisher=None
    )
    service.grant_exception(token)
    service.revoke_exception("tokenhash", revoked_by="cio", reason="revert")

    # 2. PolicyRegistryService with event_publisher = None and transition
    policy_repo = InMemoryCompliancePolicyRepository()
    auth_p2 = AuthorizationPolicy(
        policy_id="auth-2",
        policy_urn="urn:auth-2",
        state="ACTIVE",
        roles_mapping=[
            {"role": "CIO", "public_key_hex": cio_pub},
            {"role": "COMPLIANCE_OFFICER", "public_key_hex": comp_pub}
        ]
    )
    auth_repo.save(auth_p2)
    
    reg_service = PolicyRegistryService(
        policy_repo=policy_repo,
        auth_repo=auth_repo,
        event_publisher=None
    )
    policy = CompliancePolicy(
        policy_id="pol-1",
        policy_urn=PolicyURN("budget", "cost", "1.0.0"),
        state=PolicyLifecycleState.DRAFT
    )
    policy_repo.save(policy)
    
    payload = "APPROVE:urn:karsa:policy:budget:cost:1.0.0"
    cio_sig = sign_payload(cio_priv, payload)
    comp_sig = sign_payload(comp_priv, payload)
    sig_block = {"cio_signature": cio_sig, "compliance_signature": comp_sig}
    
    # Set to REVIEW first, then APPROVED (needs signatures)
    reg_service.transition_policy_state("pol-1", PolicyLifecycleState.REVIEW)
    reg_service.transition_policy_state("pol-1", PolicyLifecycleState.APPROVED, signature_block=sig_block)
    
    # Now set to ACTIVE (event_publisher is None)
    prior_policy = CompliancePolicy(
        policy_id="pol-prior",
        policy_urn=PolicyURN("budget", "cost", "1.0.0"),
        state=PolicyLifecycleState.ACTIVE
    )
    policy_repo.save(prior_policy)
    
    reg_service.transition_policy_state("pol-1", PolicyLifecycleState.ACTIVE)

def test_pdp_exception_override_checks_branches():
    import copy
    policy_repo = InMemoryCompliancePolicyRepository()
    token_repo = InMemoryExceptionTokenRepository()
    revocation_repo = InMemoryExceptionRevocationRepository()
    decision_repo = InMemoryGovernanceDecisionRecordRepository()
    
    eval_service = PolicyEvaluationService(
        policy_repo=policy_repo,
        snapshot_repo=None,
        decision_repo=decision_repo,
        token_repo=token_repo,
        revocation_repo=revocation_repo
    )
    
    # Active policy that breaches a rule
    policy = CompliancePolicy(
        policy_id="p-cost",
        policy_urn=PolicyURN.from_string("urn:karsa:policy:budget:cost:1.0.0"),
        state=PolicyLifecycleState.ACTIVE,
        scope=PolicyScope("CAPABILITY", "urn:karsa:capability:chat:v1"),
        rules=[
            PolicyRule(
                condition=PolicyCondition("estimated_cost", "GREATER_THAN", "100.0"),
                action=PolicyAction.DENY
            )
        ]
    )
    policy_repo.save(policy)
    
    # Case A: token_repo is None, evaluate returns None (line 520)
    eval_service_no_repo = PolicyEvaluationService(
        policy_repo=policy_repo,
        snapshot_repo=None,
        decision_repo=decision_repo,
        token_repo=None
    )
    dec_no_repo = eval_service_no_repo.check_execution_authorization(
        execution_id="exec-a",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"estimated_cost": 150.0, "exception_token_urn": "some-token"}
    )
    assert dec_no_repo.decision_outcome == "DENY"

    # Create a base token for testing override failures
    base_token = ExceptionToken(
        token_hash="tok-hash",
        token_urn="urn:karsa:exception:tok-hash",
        order_id="exec-b",
        state="ACTIVE",
        target_type="PORTFOLIO",
        target_urn="urn:karsa:portfolio:1",
        limit_parameter="estimated_cost",
        limit_ceiling=200.0,
        start_time=datetime.now(timezone.utc) - timedelta(hours=1),
        expire_time=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    token_repo.save(base_token)

    # Case B: Token state is not ACTIVE (line 531)
    inactive_token = copy.deepcopy(base_token)
    inactive_token.token_hash = "tok-inactive"
    inactive_token.state = "DRAFT"
    token_repo.save(inactive_token)
    dec_inactive = eval_service.check_execution_authorization(
        execution_id="exec-b",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"estimated_cost": 150.0, "exception_token_urn": "urn:karsa:exception:tok-inactive"}
    )
    assert dec_inactive.decision_outcome == "DENY"

    # Case C: Token order_id mismatch (line 534)
    dec_order_mismatch = eval_service.check_execution_authorization(
        execution_id="exec-mismatch", # mismatched order_id
        capability_urn="urn:karsa:capability:chat:v1",
        context={"estimated_cost": 150.0, "exception_token_urn": "urn:karsa:exception:tok-hash"}
    )
    assert dec_order_mismatch.decision_outcome == "DENY"

    # Case D: Token expired or not yet active (line 538)
    expired_token = copy.deepcopy(base_token)
    expired_token.token_hash = "tok-expired"
    expired_token.order_id = "exec-d"
    expired_token.start_time = datetime.now(timezone.utc) - timedelta(hours=2)
    expired_token.expire_time = datetime.now(timezone.utc) - timedelta(hours=1)
    token_repo.save(expired_token)
    dec_expired = eval_service.check_execution_authorization(
        execution_id="exec-d",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"estimated_cost": 150.0, "exception_token_urn": "urn:karsa:exception:tok-expired"}
    )
    assert dec_expired.decision_outcome == "DENY"

    # Case E: Token is revoked (line 541)
    rev_token = copy.deepcopy(base_token)
    rev_token.token_hash = "tok-revoked"
    rev_token.order_id = "exec-e"
    token_repo.save(rev_token)
    revocation = ExceptionRevocation(
        revocation_id="rev-1",
        token_hash="tok-revoked",
        revoked_by="cio",
        revoked_at=datetime.now(timezone.utc),
        reason="emergency"
    )
    revocation_repo.save(revocation)
    dec_revoked = eval_service.check_execution_authorization(
        execution_id="exec-e",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"estimated_cost": 150.0, "exception_token_urn": "urn:karsa:exception:tok-revoked"}
    )
    assert dec_revoked.decision_outcome == "DENY"

    # Case F: Token limit parameter mismatch (line 544)
    param_mismatch_token = copy.deepcopy(base_token)
    param_mismatch_token.token_hash = "tok-param"
    param_mismatch_token.order_id = "exec-f"
    param_mismatch_token.limit_parameter = "portfolio_var_95"
    token_repo.save(param_mismatch_token)
    dec_param = eval_service.check_execution_authorization(
        execution_id="exec-f",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"estimated_cost": 150.0, "exception_token_urn": "urn:karsa:exception:tok-param"}
    )
    assert dec_param.decision_outcome == "DENY"

    # Case G: Breached value > limit_ceiling (line 546)
    ceiling_token = copy.deepcopy(base_token)
    ceiling_token.token_hash = "tok-ceiling"
    ceiling_token.order_id = "exec-g"
    ceiling_token.limit_ceiling = 120.0 # breached value will be 150.0
    token_repo.save(ceiling_token)
    dec_ceiling = eval_service.check_execution_authorization(
        execution_id="exec-g",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"estimated_cost": 150.0, "exception_token_urn": "urn:karsa:exception:tok-ceiling"}
    )
    assert dec_ceiling.decision_outcome == "DENY"

def test_file_repositories_concurrency_and_exception_branches(tmp_path):
    import copy
    # 1. FileCompliancePolicyRepository ConcurrencyConflictError
    repo = FileCompliancePolicyRepository(tmp_path)
    policy = CompliancePolicy(
        policy_id="p1",
        policy_urn=PolicyURN("budget", "cost", "1.0.0"),
        state=PolicyLifecycleState.DRAFT
    )
    repo.save(policy)
    
    # Save a conflicting version
    policy_conflict = copy.deepcopy(policy)
    object.__setattr__(policy_conflict, "aggregate_version", 5)
    
    path = repo._get_path("p1")
    serialized = serialize_compliance_policy(policy_conflict)
    with open(path, "w") as f:
        json.dump(serialized, f)
        
    with pytest.raises(ConcurrencyConflictError):
        repo.save(policy)

    # Trigger OSError / JSONDecodeError in save()
    with open(path, "w") as f:
        f.write("{invalid_json}")
    repo.save(policy)

    # 2. find_by_id Exception handling
    with open(path, "w") as f:
        f.write("{invalid_json}")
    assert repo.find_by_id("p1") is None

    # 3. find_latest_by_urn Exception handling
    bad_file = repo.base_dir / "invalid.json"
    with open(bad_file, "w") as f:
        f.write("bad")
    non_json = repo.base_dir / "readme.txt"
    with open(non_json, "w") as f:
        f.write("text")
    
    repo_no_dir = FileCompliancePolicyRepository(tmp_path / "does-not-exist")
    if repo_no_dir.base_dir.exists():
        os.rmdir(repo_no_dir.base_dir)
    assert repo_no_dir.find_latest_by_urn(PolicyURN("a", "b", "1.0.0")) is None
    assert repo_no_dir.find_active_for_scope("PORTFOLIO", "urn") == []

    assert repo.find_latest_by_urn(PolicyURN("a", "b", "1.0.0")) is None
    assert repo.find_active_for_scope("PORTFOLIO", "urn") == []

    # 4. FileGovernanceDecisionRecordRepository find_by_id Exception handling
    dec_repo = FileGovernanceDecisionRecordRepository(tmp_path)
    dec = GovernanceDecisionRecord(decision_id="d1")
    dec_repo.save(dec)
    dec_path = dec_repo._get_path("d1")
    with open(dec_path, "w") as f:
        f.write("bad")
    assert dec_repo.find_by_id("d1") is None

    # 5. FileGovernanceAuditRepository append_chain ConcurrencyConflictError
    audit_repo = FileGovernanceAuditRepository(tmp_path)
    entry = GovernanceAuditChain(decision_id="d1", previous_hash="", current_hash="")
    audit_repo.append_chain(entry)
    
    entry_conflict = copy.deepcopy(entry)
    object.__setattr__(entry_conflict, "aggregate_version", 5)
    audit_path = audit_repo._get_path(entry.audit_id)
    with open(audit_path, "w") as f:
        json.dump(serialize_governance_audit_chain(entry_conflict), f)
        
    with pytest.raises(ConcurrencyConflictError):
        audit_repo.append_chain(entry)
        
    with open(audit_path, "w") as f:
        f.write("bad")
    audit_repo.append_chain(entry)

    audit_repo_no_dir = FileGovernanceAuditRepository(tmp_path / "no-audit-dir")
    if audit_repo_no_dir.base_dir.exists():
        os.rmdir(audit_repo_no_dir.base_dir)
    assert audit_repo_no_dir.get_latest_entry() is None
    
    with open(audit_path, "w") as f:
        f.write("bad")
    assert audit_repo.get_latest_entry() is None

    # 6. FileGovernanceBudgetCacheRepository find_by_workflow_id Exception handling
    budget_repo = FileGovernanceBudgetCacheRepository(tmp_path)
    cache = GovernanceBudgetCache(workflow_id="wf1", remaining_budget=100.0)
    budget_repo.save(cache)
    budget_path = budget_repo._get_path("wf1")
    with open(budget_path, "w") as f:
        f.write("bad")
    assert budget_repo.find_by_workflow_id("wf1") is None

def test_in_memory_repositories_missing_branches():
    import copy
    # 1. CompliancePolicy
    policy_repo = InMemoryCompliancePolicyRepository()
    p_active_wildcard = CompliancePolicy(
        policy_id="p-act-wc",
        policy_urn=PolicyURN("a", "b", "1.0.0"),
        state=PolicyLifecycleState.ACTIVE,
        scope=PolicyScope("PORTFOLIO", "*")
    )
    p_active_specific = CompliancePolicy(
        policy_id="p-act-spec",
        policy_urn=PolicyURN("a", "b", "1.0.0"),
        state=PolicyLifecycleState.ACTIVE,
        scope=PolicyScope("PORTFOLIO", "urn:portfolio:1")
    )
    p_inactive = CompliancePolicy(
        policy_id="p-inact",
        policy_urn=PolicyURN("a", "b", "1.0.0"),
        state=PolicyLifecycleState.DRAFT,
        scope=PolicyScope("PORTFOLIO", "*")
    )
    policy_repo.save(p_active_wildcard)
    policy_repo.save(p_active_specific)
    policy_repo.save(p_inactive)

    res = policy_repo.find_active_for_scope("PORTFOLIO", "urn:portfolio:1")
    assert len(res) == 2
    res2 = policy_repo.find_active_for_scope("PORTFOLIO", "urn:portfolio:2")
    assert len(res2) == 1

    # 2. AuthorizationPolicy find_by_id and urn not found
    auth_repo = InMemoryAuthorizationPolicyRepository()
    assert auth_repo.find_by_id("non-existent") is None
    assert auth_repo.find_by_urn("non-existent") is None
    
    auth_p = AuthorizationPolicy(policy_id="auth1", policy_urn="urn:auth1", state="DRAFT", roles_mapping=[])
    auth_repo.save(auth_p)
    assert auth_repo.find_active_policy() is None

    # 3. ExceptionToken find_active_by_order_id not found or not active
    token_repo = InMemoryExceptionTokenRepository()
    token = ExceptionToken(
        token_hash="tok",
        token_urn="urn:tok",
        order_id="order-1",
        state="DRAFT",
        target_type="PORTFOLIO",
        target_urn="*",
        limit_parameter="cost",
        limit_ceiling=10.0,
        start_time=datetime.now(timezone.utc),
        expire_time=datetime.now(timezone.utc)
    )
    token_repo.save(token)
    assert token_repo.find_active_by_order_id("order-1") is None

    # 4. ExceptionRevocation find_by_token_hash not found
    rev_repo = InMemoryExceptionRevocationRepository()
    assert rev_repo.find_by_token_hash("non-existent") is None

    # 5. RiskStateSnapshot find_by_snapshot_id not found
    snap_repo = InMemoryRiskStateSnapshotRepository()
    assert snap_repo.find_by_snapshot_id("non-existent") is None

    # 6. GovernanceAuditRepository append_chain concurrency and updates
    audit_repo = InMemoryGovernanceAuditRepository()
    entry = GovernanceAuditChain(decision_id="d1", previous_hash="", current_hash="")
    audit_repo.append_chain(entry)
    
    entry_conflict = copy.deepcopy(entry)
    object.__setattr__(entry_conflict, "aggregate_version", 5)
    with pytest.raises(ConcurrencyConflictError):
        audit_repo.append_chain(entry_conflict)

    entry_update = copy.deepcopy(entry)
    object.__setattr__(entry_update, "aggregate_version", 1)
    audit_repo.append_chain(entry_update)
    assert len(audit_repo._list) == 1

def test_pdp_additional_branches(event_bus):
    publish, events = event_bus
    policy_repo = InMemoryCompliancePolicyRepository()
    snapshot_repo = InMemoryRiskStateSnapshotRepository()
    decision_repo = InMemoryGovernanceDecisionRecordRepository()
    
    eval_service = PolicyEvaluationService(
        policy_repo=policy_repo,
        snapshot_repo=snapshot_repo,
        decision_repo=decision_repo,
        event_publisher=publish
    )

    # 1. Budget snapshot exists but find_by_workflow_id returns None
    budget_cache_repo = InMemoryGovernanceBudgetCacheRepository()
    eval_service_budget = PolicyEvaluationService(
        policy_repo=policy_repo,
        snapshot_repo=budget_cache_repo,
        decision_repo=decision_repo
    )
    dec = eval_service_budget.check_execution_authorization(
        execution_id="exec-budget-none",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"workflow_id": "wf-missing"}
    )
    assert dec.decision_outcome == "DENY"

    # 2. Setup policies including PORTFOLIO scope
    policy_portfolio = CompliancePolicy(
        policy_id="p-portfolio",
        policy_urn=PolicyURN("budget", "portfolio-limit", "1.0.0"),
        state=PolicyLifecycleState.ACTIVE,
        scope=PolicyScope("PORTFOLIO", "urn:karsa:portfolio:123"),
        rules=[
            PolicyRule(
                condition=PolicyCondition("estimated_cost", "LESS_THAN_OR_EQUAL", "50.0"),
                action=PolicyAction.ALLOW,
                priority=10
            ),
            PolicyRule(
                condition=PolicyCondition("estimated_cost", "GREATER_THAN", "5.0"),
                action=PolicyAction.DENY,
                priority=20
            )
        ]
    )
    policy_repo.save(policy_portfolio)

    # 3. Context has portfolio_id and portfolio_snapshot_id.
    context = {
        "portfolio_id": "urn:karsa:portfolio:123",
        "portfolio_var_95": 0.08,
        "estimated_cost": 10.0,
        "is_execution": True
    }
    
    dec = eval_service.check_execution_authorization(
        execution_id="exec-portfolio-check",
        capability_urn="urn:karsa:capability:chat:v1",
        context=context
    )
    assert dec.decision_outcome == "DENY"
    denied_events = [e for e in events if e.__class__.__name__ == "CapabilityExecutionDeniedEvent"]
    assert len(denied_events) > 0

    # 4. _evaluate_exception_override where token URN does not start with urn:karsa:exception:
    token_repo = InMemoryExceptionTokenRepository()
    eval_service.token_repo = token_repo
    
    token = ExceptionToken(
        token_hash="rawhash",
        token_urn="urn:karsa:exception:rawhash",
        order_id="exec-raw",
        state="ACTIVE",
        target_type="PORTFOLIO",
        target_urn="*",
        limit_parameter="estimated_cost",
        limit_ceiling=15.0,
        start_time=datetime.now(timezone.utc) - timedelta(hours=1),
        expire_time=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    token_repo.save(token)
    
    context_raw = {
        "portfolio_id": "urn:karsa:portfolio:123",
        "portfolio_var_95": 0.08,
        "estimated_cost": 10.0,
        "exception_token_urn": "rawhash"
    }
    dec_raw = eval_service.check_execution_authorization(
        execution_id="exec-raw",
        capability_urn="urn:karsa:capability:chat:v1",
        context=context_raw
    )
    assert dec_raw.decision_outcome == "ALLOW_VIA_EXCEPTION"
