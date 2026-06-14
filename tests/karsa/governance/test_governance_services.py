import time
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from karsa.shared.infrastructure.uow import ConcurrencyConflictError
from karsa.governance.domain.models import (
    PolicyURN, PolicyLifecycleState, PolicyDefinition, PolicyScope, PolicyRule,
    PolicyCondition, PolicyAction, GovernanceDecision, GovernanceAuditChain,
    GovernanceBudgetCache
)
from karsa.governance.infrastructure.repositories import (
    InMemoryPolicyDefinitionRepository, InMemoryGovernanceDecisionRepository,
    InMemoryGovernanceAuditRepository, InMemoryGovernanceBudgetCacheRepository,
    FilePolicyDefinitionRepository, FileGovernanceDecisionRepository,
    FileGovernanceAuditRepository, FileGovernanceBudgetCacheRepository
)
from karsa.governance.application.services import (
    PolicyRegistryService, PolicyEvaluationService, GovernanceAuditService
)

@pytest.fixture
def memory_repos():
    return (
        InMemoryPolicyDefinitionRepository(),
        InMemoryGovernanceDecisionRepository(),
        InMemoryGovernanceAuditRepository(),
        InMemoryGovernanceBudgetCacheRepository()
    )

@pytest.fixture
def file_repos(tmp_path):
    return (
        FilePolicyDefinitionRepository(tmp_path),
        FileGovernanceDecisionRepository(tmp_path),
        FileGovernanceAuditRepository(tmp_path),
        FileGovernanceBudgetCacheRepository(tmp_path)
    )

@pytest.fixture
def event_bus():
    events = []
    def publish(event):
        events.append(event)
    return publish, events


# 1. Policy Registry Service FSM
def test_policy_registration_and_state_transitions(memory_repos, event_bus):
    policy_repo, decision_repo, audit_repo, cache_repo = memory_repos
    publish, events = event_bus
    registry = PolicyRegistryService(policy_repo, event_publisher=publish)

    scope = PolicyScope("CAPABILITY", "urn:karsa:capability:chat:v1")
    rules = [PolicyRule(action=PolicyAction.DENY)]
    
    # Register policy
    policy = registry.register_policy(
        policy_id="pol-1",
        urn_str="urn:karsa:policy:budget:max_cost:1.0.0",
        priority=100,
        scope=scope,
        rules=rules
    )
    assert policy.state == PolicyLifecycleState.DRAFT
    assert policy_repo.find_by_id("pol-1") is not None
    assert len(events) == 1
    assert events[0].__class__.__name__ == "PolicyCreatedEvent"

    # Transition state
    registry.transition_policy_state("pol-1", PolicyLifecycleState.REVIEW, "Review requested")
    registry.transition_policy_state("pol-1", PolicyLifecycleState.APPROVED, "Approved", signature_block={"cio_signature": "sig", "compliance_signature": "sig"})
    registry.transition_policy_state("pol-1", PolicyLifecycleState.ACTIVE, "Approval granted")

    loaded = policy_repo.find_by_id("pol-1")
    assert loaded.state == PolicyLifecycleState.ACTIVE
    assert len(events) == 2
    assert events[1].__class__.__name__ == "PolicyActivatedEvent"


# 2. Policy Evaluation
def test_evaluation_deny_by_default(memory_repos):
    policy_repo, decision_repo, audit_repo, cache_repo = memory_repos
    evaluation_service = PolicyEvaluationService(policy_repo, cache_repo)

    # When no active policies match, evaluate returns DENY_BY_DEFAULT
    decision = evaluation_service.check_execution_authorization(
        execution_id="exec-1",
        capability_urn="urn:karsa:capability:chat:v1",
        context={}
    )
    assert decision.outcome == "DENIED"
    assert "DENY_BY_DEFAULT" in decision.reason

def test_evaluation_allow_and_deny_rules(memory_repos):
    policy_repo, decision_repo, audit_repo, cache_repo = memory_repos
    evaluation_service = PolicyEvaluationService(policy_repo, cache_repo)

    # Add active policy restricting costs over $0.05
    policy = PolicyDefinition(
        policy_id="pol-1",
        policy_urn=PolicyURN("budget", "max_cost", "1.0.0"),
        scope=PolicyScope("CAPABILITY", "urn:karsa:capability:chat:v1"),
        priority=100,
        rules=[
            PolicyRule(
                condition=PolicyCondition(attribute="estimated_cost", operator="GREATER_THAN", value="0.05"),
                action=PolicyAction.DENY
            )
        ]
    )
    # Bypass immutability to set state active
    object.__setattr__(policy, "state", PolicyLifecycleState.ACTIVE)
    policy_repo.save(policy)

    # Context cost $0.02 <= $0.05 -> ALLOW (outcome = APPROVED)
    decision1 = evaluation_service.check_execution_authorization(
        execution_id="exec-1",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"estimated_cost": 0.02}
    )
    assert decision1.outcome == "APPROVED"

    # Context cost $0.08 > $0.05 -> DENY (outcome = DENIED)
    decision2 = evaluation_service.check_execution_authorization(
        execution_id="exec-2",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"estimated_cost": 0.08}
    )
    assert decision2.outcome == "DENIED"
    assert "PolicyDeny" in decision2.reason


# 3. Policy Conflicts
def test_conflict_resolution_deny_overrides(memory_repos):
    policy_repo, decision_repo, audit_repo, cache_repo = memory_repos
    evaluation_service = PolicyEvaluationService(policy_repo, cache_repo)

    # Policy 1: DENY rule
    p1 = PolicyDefinition(
        policy_id="pol-1",
        policy_urn=PolicyURN("budget", "max_cost", "1.0.0"),
        scope=PolicyScope("CAPABILITY", "urn:karsa:capability:chat:v1"),
        priority=10,
        rules=[
            PolicyRule(
                condition=PolicyCondition(attribute="cost", operator="GREATER_THAN", value="5.0"),
                action=PolicyAction.DENY
            )
        ]
    )
    # Policy 2: ALLOW rule (implied since it has no DENY rules matching)
    p2 = PolicyDefinition(
        policy_id="pol-2",
        policy_urn=PolicyURN("budget", "allow_always", "1.0.0"),
        scope=PolicyScope("CAPABILITY", "urn:karsa:capability:chat:v1"),
        priority=10,  # Same priority
        rules=[]
    )
    object.__setattr__(p1, "state", PolicyLifecycleState.ACTIVE)
    object.__setattr__(p2, "state", PolicyLifecycleState.ACTIVE)
    policy_repo.save(p1)
    policy_repo.save(p2)

    # If both apply, Deny-Overrides matches and outcome becomes DENIED
    decision = evaluation_service.check_execution_authorization(
        execution_id="exec-1",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"cost": 10.0}
    )
    assert decision.outcome == "DENIED"


# 4. Budget constraints and stale snap checks
def test_budget_constraints_and_staleness(memory_repos):
    policy_repo, decision_repo, audit_repo, cache_repo = memory_repos
    evaluation_service = PolicyEvaluationService(policy_repo, cache_repo)

    # Register active policy
    policy = PolicyDefinition(
        policy_id="pol-1",
        policy_urn=PolicyURN("budget", "max_cost", "1.0.0"),
        scope=PolicyScope("CAPABILITY", "urn:karsa:capability:chat:v1"),
        priority=100,
        rules=[]
    )
    object.__setattr__(policy, "state", PolicyLifecycleState.ACTIVE)
    policy_repo.save(policy)

    # Save cache snapshot: $0.05 remaining budget
    cache_repo.save(GovernanceBudgetCache(workflow_id="wf-1", remaining_budget=0.05))

    # Evaluate cost $0.08 > $0.05 cache remaining -> DENY
    decision1 = evaluation_service.check_execution_authorization(
        execution_id="exec-1",
        capability_urn="urn:karsa:capability:chat:v1",
        context={"workflow_id": "wf-1", "estimated_cost": 0.08}
    )
    assert decision1.outcome == "DENIED"
    assert "BudgetExceeded" in decision1.reason

    # Test Stale cache snap check
    stale_cache = GovernanceBudgetCache(
        workflow_id="wf-stale",
        remaining_budget=10.0,
        last_updated_at=datetime.now(timezone.utc) - timedelta(seconds=120)
    )
    cache_repo.save(stale_cache)

    with pytest.raises(Exception) as exc_info:
        evaluation_service.check_execution_authorization(
            execution_id="exec-2",
            capability_urn="urn:karsa:capability:chat:v1",
            context={"workflow_id": "wf-stale", "estimated_cost": 1.0}
        )
    assert "StaleBudgetSnapshotError" in str(exc_info.value)


# 5. Replay Bypass
def test_replay_bypass(memory_repos):
    policy_repo, decision_repo, audit_repo, cache_repo = memory_repos
    evaluation_service = PolicyEvaluationService(policy_repo, cache_repo)

    historical = GovernanceDecision(
        decision_id="hist-dec-1",
        execution_id="exec-1",
        outcome="APPROVED",
        reason="Historical Selection"
    )

    # In replay mode, PDP checks are bypassed, returns historical directly
    decision = evaluation_service.check_execution_authorization(
        execution_id="exec-1",
        capability_urn="urn:karsa:capability:chat:v1",
        context={},
        replay_mode=True,
        historical_decision=historical
    )
    assert decision == historical
    assert decision.decision_id == "hist-dec-1"


# 6. Emergency Override
def test_emergency_override(memory_repos, tmp_path):
    policy_repo, decision_repo, audit_repo, cache_repo = memory_repos
    bypass_log = tmp_path / "bypass_audit.log"
    evaluation_service = PolicyEvaluationService(
        policy_repo, cache_repo, bypass_log_path=str(bypass_log)
    )

    decision = evaluation_service.check_execution_authorization(
        execution_id="exec-override",
        capability_urn="urn:karsa:capability:chat:v1",
        context={},
        override_token="admin-override-token-secret-key"
    )
    assert decision.outcome == "APPROVED"
    assert decision.reason == "EMERGENCY_OVERRIDE_GRANTED"
    assert bypass_log.exists()
    
    with open(bypass_log, "r") as f:
        log_content = f.read()
    assert "OVERRIDE" in log_content
    assert "exec-override" in log_content


# 7. Asynchronous Audit Chain
def test_async_audit_chain_projection(memory_repos):
    policy_repo, decision_repo, audit_repo, cache_repo = memory_repos
    audit_service = GovernanceAuditService(audit_repo)

    # Match active policy
    policy = PolicyDefinition(
        policy_id="pol-1",
        policy_urn=PolicyURN("budget", "max_cost", "1.0.0"),
        scope=PolicyScope("CAPABILITY", "urn:karsa:capability:chat:v1"),
        priority=100,
        rules=[]
    )
    object.__setattr__(policy, "state", PolicyLifecycleState.ACTIVE)
    policy_repo.save(policy)

    evaluation_service = PolicyEvaluationService(
        policy_repo, cache_repo, audit_service=audit_service
    )

    # Trigger decision evaluation
    decision = evaluation_service.check_execution_authorization(
        execution_id="exec-1",
        capability_urn="urn:karsa:capability:chat:v1",
        context={}
    )
    
    # Wait for the async worker thread to write the Layer B chained log
    time.sleep(0.1)

    latest = audit_repo.get_latest_entry()
    assert latest is not None
    assert latest.decision_id == decision.decision_id
    assert latest.current_hash == GovernanceAuditChain.calculate_hash(
        decision.decision_id, decision.outcome, ""
    )

    # Evaluate another decision
    decision2 = evaluation_service.check_execution_authorization(
        execution_id="exec-2",
        capability_urn="urn:karsa:capability:chat:v1",
        context={}
    )
    
    time.sleep(0.1)

    latest2 = audit_repo.get_latest_entry()
    assert latest2 is not None
    assert latest2.decision_id == decision2.decision_id
    assert latest2.previous_hash == latest.current_hash
    assert latest2.current_hash == GovernanceAuditChain.calculate_hash(
        decision2.decision_id, decision2.outcome, latest.current_hash
    )


# 8. Repositories Persistence & OCC
def test_policy_in_memory_persistence_and_occ(memory_repos):
    policy_repo, decision_repo, audit_repo, cache_repo = memory_repos
    policy = PolicyDefinition(
        policy_id="pol-1",
        policy_urn=PolicyURN("budget", "max_cost", "1.0.0"),
        state=PolicyLifecycleState.DRAFT
    )
    policy_repo.save(policy)

    loaded = policy_repo.find_by_id("pol-1")
    assert loaded.aggregate_version == 0

    loaded.transition_to(PolicyLifecycleState.REVIEW)
    policy_repo.save(loaded)  # Saved version = 1

    policy.priority = 200
    with pytest.raises(ConcurrencyConflictError):
        policy_repo.save(policy)

def test_policy_file_persistence_and_occ(file_repos):
    policy_repo, decision_repo, audit_repo, cache_repo = file_repos
    policy = PolicyDefinition(
        policy_id="pol-1",
        policy_urn=PolicyURN("budget", "max_cost", "1.0.0"),
        state=PolicyLifecycleState.DRAFT
    )
    policy_repo.save(policy)

    path = policy_repo.base_dir / "pol-1.json"
    assert path.exists()

    loaded = policy_repo.find_by_id("pol-1")
    assert loaded.aggregate_version == 0

    loaded.transition_to(PolicyLifecycleState.REVIEW)
    policy_repo.save(loaded)

    with pytest.raises(ConcurrencyConflictError):
        policy_repo.save(policy)
