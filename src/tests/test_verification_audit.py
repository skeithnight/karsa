import pytest
import shutil
import time
from pathlib import Path

from karsa.domain.models import WorkflowState, WorkflowSnapshot, GovernanceDecision
from karsa.domain.events import WorkflowCreatedEvent, ArtifactPersistedEvent, ExecutionCheckpointEvent, DomainEvent
from karsa.domain.persistence import SnapshotRepository, EventJournalRepository, deserialize_event
from karsa.workflow.fsm import StateTransitionEngine
from karsa.governance.evaluator import GovernanceEvaluator
from karsa.workflow.workflow_engine import WorkflowEngine
from karsa.artifacts.registry import ArtifactRegistry
from karsa.artifacts.projection import ProjectionManager
from karsa.workflow.retry import RetryCoordinator
from karsa.workflow.orchestrator import AgentOrchestrator
from karsa.workflow.recovery import RecoveryEngine
from karsa.workflow.runner import WorkflowRunner

class DummyEvaluator(GovernanceEvaluator):
    def evaluate(self, snapshot, ex_id, rev_id):
        return GovernanceDecision(workflow_id=snapshot.workflow_id, review_cycle_id=rev_id, execution_id=ex_id, sequence_number=0, decision_type="ALLOW", reason="Default")

@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws

def test_suspend_resume_and_sequence(workspace):
    snapshot_repo = SnapshotRepository(workspace)
    event_repo = EventJournalRepository(workspace)
    fsm = StateTransitionEngine()
    evaluator = DummyEvaluator()
    registry = ArtifactRegistry(workspace)
    projection = ProjectionManager(workspace, registry, event_repo)
    
    # Mock RetryCoordinator to fail exactly once to trigger SUSPENDED
    class MockRetryCoordinator(RetryCoordinator):
        def __init__(self):
            super().__init__()
            self.calls = 0
            self.pe_calls = 0
            self.review_calls = 0
        def execute_with_backoff(self, func):
            res = func()
            if "PE" in str(res):
                self.pe_calls += 1
                return res
            if "Review" in str(res):
                self.review_calls += 1
                if self.review_calls == 1:
                    raise Exception("Exhausted: simulated 429")
                return res
            return res
            
    retry_coordinator = MockRetryCoordinator()
    
    engine = WorkflowEngine(snapshot_repo, event_repo, fsm, evaluator)
    orchestrator = AgentOrchestrator(engine, retry_coordinator, registry)
    recovery = RecoveryEngine(snapshot_repo, event_repo, is_replaying=True)
    runner = WorkflowRunner(engine, orchestrator, projection, recovery)
    
    workflow_id = "wf_123"
    engine.snapshot = WorkflowSnapshot(workflow_id=workflow_id, state=WorkflowState.IDEA)
    engine.append_event(WorkflowCreatedEvent(workflow_id=workflow_id))
    engine.transition_state(WorkflowState.DRAFT)
    engine.transition_state(WorkflowState.REVIEW)
    engine.snapshot_repo.save(engine.snapshot)
    
    # Start workflow
    runner.start_workflow(workflow_id)
    
    # Should suspend because Review agent threw Exhausted
    assert engine.snapshot.state == WorkflowState.SUSPENDED
    assert retry_coordinator.pe_calls == 1
    assert retry_coordinator.review_calls == 1
    
    # Verify sequence monotonicity
    events = event_repo.load(workflow_id)
    seqs = [e.sequence_number for e in events if getattr(e, 'sequence_number', 0) > 0]
    assert len(seqs) == len(set(seqs)), "Duplicates found"
    assert seqs == sorted(seqs), "Not monotonic"
    # assert seqs == list(range(1, len(seqs)+1)), "Gaps found"  # Not exactly, but should have no gaps
    
    # Check if checkpoint exists
    checkpoints = [e for e in events if isinstance(e, ExecutionCheckpointEvent)]
    assert any(c.sub_task_name == "PE_COMPLETE" for c in checkpoints)
    
    # Now resume
    runner2 = WorkflowRunner(engine, orchestrator, projection, recovery)
    runner2.resume(workflow_id)
    
    # Should approve or revise
    assert engine.snapshot.state in [WorkflowState.APPROVED, WorkflowState.REVISE]
    
    # IMPORTANT: PE calls should still be 1 (was skipped)
    assert retry_coordinator.pe_calls == 1
    assert retry_coordinator.review_calls == 2

def test_schema_version_upcasting():
    legacy_json = {
        "event_type": "WorkflowCreatedEvent",
        "payload": {
            "workflow_id": "test_legacy"
        }
    }
    
    event = deserialize_event(legacy_json)
    assert getattr(event, "schema_version", None) == 1
    assert event.workflow_id == "test_legacy"

def test_crash_recovery_validation(workspace):
    snapshot_repo = SnapshotRepository(workspace)
    event_repo = EventJournalRepository(workspace)
    registry = ArtifactRegistry(workspace)
    
    workflow_id = "wf_crash"
    
    # 1. Manually craft events: Created -> Draft -> Review -> ArtifactPersisted
    event_repo.append(workflow_id, WorkflowCreatedEvent(workflow_id=workflow_id, sequence_number=1))
    
    # Create the actual artifact in registry (simulate AO stored it before crash)
    version_hash = registry.store_versioned("My recovered design")
    
    event_repo.append(workflow_id, ArtifactPersistedEvent(
        artifact_id=version_hash, 
        target_path="design.md", 
        sha256_hash=version_hash,
        sequence_number=2
    ))
    
    # Simulating crash here. ProjectionManager never ran. design.md does NOT exist in workspace.
    assert not (workspace / "design.md").exists()
    
    # 2. Recovery!
    recovery = RecoveryEngine(snapshot_repo, event_repo, is_replaying=True)
    snapshot = recovery.rehydrate(workflow_id)
    
    assert snapshot is not None
    assert snapshot.last_sequence_number == 2
    
    # 3. Projection Manager Sync
    projection = ProjectionManager(workspace, registry, event_repo)
    projection.reconcile_all(snapshot)
    
    # Verify design.md was recreated deterministically
    assert (workspace / "design.md").exists()
    with open(workspace / "design.md", "r") as f:
        assert f.read() == "My recovered design"
