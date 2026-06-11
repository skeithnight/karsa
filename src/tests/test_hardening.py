import pytest
import os
import time
from pathlib import Path

from karsa.domain.models import WorkflowState, WorkflowSnapshot, GovernanceDecision
from karsa.domain.events import WorkflowCreatedEvent, ArtifactPersistedEvent, ExecutionCheckpointEvent
from karsa.domain.persistence import SnapshotRepository, EventJournalRepository
from karsa.workflow.fsm import StateTransitionEngine
from karsa.governance.evaluator import GovernanceEvaluator
from karsa.workflow.workflow_engine import WorkflowEngine
from karsa.artifacts.registry import ArtifactRegistry
from karsa.artifacts.projection import ProjectionManager
from karsa.workflow.retry import RetryCoordinator, ProviderExhaustedException
from karsa.workflow.orchestrator import AgentOrchestrator
from karsa.workflow.recovery import RecoveryEngine
from karsa.workflow.runner import WorkflowRunner
from karsa.workflow.snapshot_strategy import SnapshotStrategyConfig

class DummyEvaluator(GovernanceEvaluator):
    def evaluate(self, snapshot, ex_id, rev_id):
        return GovernanceDecision(workflow_id=snapshot.workflow_id, review_cycle_id=rev_id, execution_id=ex_id, sequence_number=0, decision_type="ALLOW", reason="Default")

@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws

# ================= RetryCoordinator Tests =================
def test_retry_coordinator_success():
    rc = RetryCoordinator(max_attempts=3, base_delay=0)
    res = rc.execute_with_backoff(lambda: "Success")
    assert res == "Success"

def test_retry_coordinator_success_after_retries():
    rc = RetryCoordinator(max_attempts=3, base_delay=0)
    attempts = [0]
    def func():
        attempts[0] += 1
        if attempts[0] < 2:
            raise Exception("429 Too Many Requests")
        return "Success"
    
    res = rc.execute_with_backoff(func)
    assert res == "Success"
    assert attempts[0] == 2

def test_retry_coordinator_exhausted():
    rc = RetryCoordinator(max_attempts=2, base_delay=0)
    def func():
        raise Exception("429 Too Many Requests")
        
    with pytest.raises(ProviderExhaustedException):
        rc.execute_with_backoff(func)

def test_retry_coordinator_non_retryable():
    rc = RetryCoordinator(max_attempts=3, base_delay=0)
    def func():
        raise ValueError("Invalid format")
        
    with pytest.raises(ValueError):
        rc.execute_with_backoff(func)

# ================= AgentOrchestrator & Runner Tests =================
def test_orchestrator_escalation(workspace):
    snapshot_repo = SnapshotRepository(workspace)
    event_repo = EventJournalRepository(workspace)
    fsm = StateTransitionEngine()
    evaluator = DummyEvaluator()
    registry = ArtifactRegistry(workspace)
    projection = ProjectionManager(workspace, registry, event_repo)
    rc = RetryCoordinator(max_attempts=1, base_delay=0)
    
    engine = WorkflowEngine(snapshot_repo, event_repo, fsm, evaluator)
    orchestrator = AgentOrchestrator(engine, rc, registry)
    runner = WorkflowRunner(engine, orchestrator, projection, RecoveryEngine(snapshot_repo, event_repo, True))
    
    # Mocking orchestrator to force revise until escalate
    original_execute = orchestrator.execute_cycle
    def mock_execute(cycle_id):
        if cycle_id > 3:
            return "ESCALATED"
        return "REVISE"
    orchestrator.execute_cycle = mock_execute
    
    workflow_id = "wf_esc"
    engine.snapshot = WorkflowSnapshot(workflow_id=workflow_id, state=WorkflowState.REVIEW)
    engine.snapshot_repo.save(engine.snapshot)
    runner.start_workflow(workflow_id)
    assert engine.snapshot.state == WorkflowState.ESCALATED

def test_orchestrator_user_override(workspace):
    snapshot_repo = SnapshotRepository(workspace)
    event_repo = EventJournalRepository(workspace)
    engine = WorkflowEngine(snapshot_repo, event_repo, StateTransitionEngine(), DummyEvaluator())
    registry = ArtifactRegistry(workspace)
    
    # Pre-populate original hash
    original_hash = registry.store_versioned("Original content")
    engine.snapshot = WorkflowSnapshot(workflow_id="wf_ovr", state=WorkflowState.REVIEW)
    engine.append_event(WorkflowCreatedEvent(workflow_id="wf_ovr"))
    engine.append_event(ArtifactPersistedEvent(target_path="design.md", sha256_hash=original_hash))
    
    # User modifies live file
    design_path = workspace / "design.md"
    design_path.parent.mkdir(parents=True, exist_ok=True)
    with open(design_path, "w") as f:
        f.write("Modified content")
        
    orchestrator = AgentOrchestrator(engine, RetryCoordinator(), registry)
    
    # Hook cycle execute
    class MockRetry:
        def execute_with_backoff(self, f): return "ok"
    orchestrator.retry_coordinator = MockRetry()
    
    orchestrator.execute_cycle(1)
    
    # Should have emitted override
    events = event_repo.load("wf_ovr")
    overrides = [e for e in events if type(e).__name__ == "UserOverrideEvent"]
    assert len(overrides) == 1
    assert overrides[0].artifact_name == "design.md"

def test_workflow_runner_suspend_resume(workspace):
    engine = WorkflowEngine(SnapshotRepository(workspace), EventJournalRepository(workspace), StateTransitionEngine(), DummyEvaluator())
    registry = ArtifactRegistry(workspace)
    orchestrator = AgentOrchestrator(engine, RetryCoordinator(), registry)
    runner = WorkflowRunner(engine, orchestrator, ProjectionManager(workspace, registry, engine.event_repo), RecoveryEngine(engine.snapshot_repo, engine.event_repo, True))
    
    engine.snapshot = WorkflowSnapshot(workflow_id="wf_susp", state=WorkflowState.REVIEW)
    engine.append_event(WorkflowCreatedEvent(workflow_id="wf_susp"))
    
    runner.suspend()
    engine.snapshot_repo.save(engine.snapshot)
    assert engine.snapshot.state == WorkflowState.SUSPENDED
    
    runner.orchestrator.execute_cycle = lambda c: "APPROVED"
    runner.resume("wf_susp")
    assert engine.snapshot is not None
    assert engine.snapshot.state == WorkflowState.APPROVED

# ================= Fault Injection & Compaction Suite =================

def test_snapshot_compaction_and_recovery(workspace):
    snapshot_repo = SnapshotRepository(workspace)
    event_repo = EventJournalRepository(workspace)
    engine = WorkflowEngine(snapshot_repo, event_repo, StateTransitionEngine(), DummyEvaluator())
    engine.snapshot_strategy.config.event_count_threshold = 3 # Trigger fast snapshot
    
    workflow_id = "wf_comp"
    engine.snapshot = WorkflowSnapshot(workflow_id=workflow_id, state=WorkflowState.IDEA)
    engine.append_event(WorkflowCreatedEvent(workflow_id=workflow_id))
    engine.transition_state(WorkflowState.DRAFT)
    engine.transition_state(WorkflowState.REVIEW) # This is 3 events -> Should trigger snapshot save
    
    # Check if snapshot file exists
    assert (workspace / ".karsa" / "workflows" / workflow_id / "snapshot.json").exists()
    
    # Add one more event to have something un-snapshotted
    engine.transition_state(WorkflowState.REVISE)
    
    # Recover
    recovery = RecoveryEngine(snapshot_repo, event_repo, True)
    recovered = recovery.rehydrate(workflow_id)
    assert recovered.state == WorkflowState.REVISE
    assert recovered.last_sequence_number == 4

