import pytest
import shutil
import json
from pathlib import Path
from dataclasses import FrozenInstanceError

from karsa.domain.models import WorkflowState, WorkflowSnapshot, GovernancePolicy, GovernancePolicySnapshot, GovernanceDecision, ViolationContext
from karsa.domain.events import GovernanceDecisionEvent, WorkflowAbortedEvent, StateTransitionedEvent
from karsa.domain.persistence import SnapshotRepository, EventJournalRepository
from karsa.workflow.fsm import StateTransitionEngine
from karsa.workflow.recovery import RecoveryEngine
from karsa.workflow.workflow_engine import WorkflowEngine
from karsa.governance.config import ConfigurationLoader
from karsa.governance.evaluator import GovernanceEvaluator
from karsa.governance.projection import GovernanceDecisionRepository

TEST_WORKSPACE = Path("test_s3_workspace")
TOML_PATH = TEST_WORKSPACE / "karsa.toml"

@pytest.fixture(autouse=True)
def setup_teardown():
    if TEST_WORKSPACE.exists():
        shutil.rmtree(TEST_WORKSPACE)
    TEST_WORKSPACE.mkdir(parents=True)
    yield
    if TEST_WORKSPACE.exists():
        shutil.rmtree(TEST_WORKSPACE)

# === Unit Tests ===

def test_policy_snapshot_creation_and_hash():
    loader = ConfigurationLoader(TOML_PATH)
    # create default
    snap1 = loader.create_snapshot("1.0")
    assert snap1.policy_version == "1.0"
    assert snap1.max_workflow_cost == 0.0
    
    # Write some toml
    with open(TOML_PATH, "w") as f:
        f.write("max_workflow_cost = 5.5\nmax_workflow_tokens = 1000\n")
        
    snap2 = loader.create_snapshot("1.0")
    assert snap2.max_workflow_cost == 5.5
    assert snap2.max_workflow_tokens == 1000
    assert snap1.policy_hash != snap2.policy_hash

def test_immutable_governance_decision():
    dec = GovernanceDecision("w1", "r1", "e1", 1, "ALLOW", "OK")
    with pytest.raises(FrozenInstanceError):
        dec.decision_type = "DENY"

def test_evaluator_allow():
    evaluator = GovernanceEvaluator()
    loader = ConfigurationLoader(TOML_PATH)
    with open(TOML_PATH, "w") as f:
        f.write("max_workflow_cost = 5.5\n")
    policy = loader.create_snapshot()
    
    snap = WorkflowSnapshot("w1", WorkflowState.IDEA, policy=policy, data={"metrics": {"total_cost": 2.0}})
    decision = evaluator.evaluate(snap, "e1", "r1")
    assert decision.decision_type == "ALLOW"

def test_evaluator_deny_and_violation_context():
    evaluator = GovernanceEvaluator()
    loader = ConfigurationLoader(TOML_PATH)
    with open(TOML_PATH, "w") as f:
        f.write("max_workflow_cost = 5.5\n")
    policy = loader.create_snapshot()
    
    snap = WorkflowSnapshot("w1", WorkflowState.IDEA, policy=policy, data={"metrics": {"total_cost": 6.0}})
    decision = evaluator.evaluate(snap, "e1", "r1")
    assert decision.decision_type == "DENY"
    assert decision.violation_context.limit_name == "max_workflow_cost"
    assert decision.violation_context.limit_value == 5.5
    assert decision.violation_context.actual_value == 6.0

# === Integration Tests ===

def test_workflow_engine_aborts():
    snap_repo = SnapshotRepository(TEST_WORKSPACE)
    event_repo = EventJournalRepository(TEST_WORKSPACE)
    fsm = StateTransitionEngine()
    evaluator = GovernanceEvaluator()
    
    engine = WorkflowEngine(snap_repo, event_repo, fsm, evaluator)
    
    loader = ConfigurationLoader(TOML_PATH)
    with open(TOML_PATH, "w") as f:
        f.write("max_review_cycles = 3\n")
    policy = loader.create_snapshot()
    
    snap = WorkflowSnapshot("w_int", WorkflowState.REVIEW, policy=policy, data={"metrics": {"execution_count": 3}})
    snap_repo.save(snap)
    engine.load("w_int")
    
    # Process
    executed = False
    def step():
        nonlocal executed
        executed = True
        
    engine.process("e1", "r1", step)
    
    assert not executed
    assert engine._snapshot.state == WorkflowState.ABORTED
    
    # Check events
    events = event_repo.load("w_int")
    assert len(events) == 3 # GovDecision, StateTransition, WorkflowAborted
    assert isinstance(events[0], GovernanceDecisionEvent)
    assert events[0].decision.decision_type == "DENY"
    assert isinstance(events[1], StateTransitionedEvent)
    assert events[1].new_state == WorkflowState.ABORTED
    assert isinstance(events[2], WorkflowAbortedEvent)

# === Durability & Adversarial Tests ===

def test_policy_changes_do_not_affect_recovery():
    snap_repo = SnapshotRepository(TEST_WORKSPACE)
    event_repo = EventJournalRepository(TEST_WORKSPACE)
    fsm = StateTransitionEngine()
    evaluator = GovernanceEvaluator()
    
    # Initial Policy
    loader = ConfigurationLoader(TOML_PATH)
    with open(TOML_PATH, "w") as f:
        f.write("max_workflow_cost = 5.0\n")
    policy = loader.create_snapshot()
    
    snap = WorkflowSnapshot("w_adv", WorkflowState.REVIEW, policy=policy, data={"metrics": {"total_cost": 4.0}}, last_sequence_number=10)
    snap_repo.save(snap)
    
    # Change TOML
    with open(TOML_PATH, "w") as f:
        f.write("max_workflow_cost = 3.0\n")
        
    # Rehydrate
    recovery = RecoveryEngine(snap_repo, event_repo, is_replaying=True)
    rec_snap = recovery.rehydrate("w_adv")
    
    # Ensure policy frozen
    assert rec_snap.policy.max_workflow_cost == 5.0
    
    # Run evaluator on recovered snap, should ALLOW (because it uses frozen 5.0, not live 3.0)
    decision = evaluator.evaluate(rec_snap, "e2", "r2")
    assert decision.decision_type == "ALLOW"

def test_governance_decisions_replay_deterministically():
    snap_repo = SnapshotRepository(TEST_WORKSPACE)
    event_repo = EventJournalRepository(TEST_WORKSPACE)
    
    loader = ConfigurationLoader(TOML_PATH)
    policy = loader.create_snapshot()
    snap = WorkflowSnapshot("w_replay", WorkflowState.IDEA, policy=policy, last_sequence_number=10)
    snap_repo.save(snap)
    
    decision = GovernanceDecision("w_replay", "r1", "e1", 11, "DENY", "Test")
    event_repo.append("w_replay", GovernanceDecisionEvent(decision, sequence_number=11))
    event_repo.append("w_replay", StateTransitionedEvent("w_replay", WorkflowState.IDEA, WorkflowState.ABORTED, "Test", sequence_number=12))
    event_repo.append("w_replay", WorkflowAbortedEvent("w_replay", "Test", sequence_number=13))
    
    recovery = RecoveryEngine(snap_repo, event_repo, is_replaying=True)
    rec_snap = recovery.rehydrate("w_replay")
    
    assert rec_snap.state == WorkflowState.ABORTED
    assert rec_snap.last_sequence_number == 13

def test_governance_projection():
    snap_repo = SnapshotRepository(TEST_WORKSPACE)
    event_repo = EventJournalRepository(TEST_WORKSPACE)
    
    decision = GovernanceDecision("w_proj", "r1", "e1", 11, "DENY", "Test")
    event_repo.append("w_proj", GovernanceDecisionEvent(decision, sequence_number=11))
    
    proj = GovernanceDecisionRepository(event_repo)
    decisions = proj.get_decisions("w_proj")
    
    assert len(decisions) == 1
    assert decisions[0].decision_type == "DENY"
