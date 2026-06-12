import pytest
from pathlib import Path
import tempfile
import shutil

from karsa.domain.persistence import SnapshotRepository, EventJournalRepository
from karsa.domain.models import WorkflowState, WorkflowSnapshot
from karsa.domain.events import WorkflowCreatedEvent
from karsa.workflow.fsm import StateTransitionEngine
from karsa.governance.evaluator import GovernanceEvaluator
from karsa.domain.models import GovernanceDecision
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

class MockProvider:
    def __init__(self, workspace):
        self.workspace = workspace
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if "Product Engineer" in prompt:
            # Generate python code
            if self.calls <= 2:
                # Cycle 1: Missing test
                return """<file path="duplicate_finder.py">
import sys
def find_duplicates():
    print("Finding...")
</file>"""
            else:
                # Cycle 2: Working code with passing tests
                return """<file path="duplicate_finder.py">
import sys
def find_duplicates():
    return []
</file>
<file path="test_duplicate_finder.py">
from duplicate_finder import find_duplicates
def test_find_duplicates():
    assert find_duplicates() == []
</file>"""
        else:
            # Review Agent
            if self.calls <= 2:
                return '{"decision": "REVISE", "convergence_score": 0.5, "blocking_issues": ["No pytest coverage"]}'
            else:
                return '{"decision": "APPROVED", "convergence_score": 1.0, "blocking_issues": []}'

def test_e2e_delivery():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        snapshot_repo = SnapshotRepository(workspace)
        event_repo = EventJournalRepository(workspace)
        engine = WorkflowEngine(snapshot_repo, event_repo, StateTransitionEngine(), DummyEvaluator())
        registry = ArtifactRegistry(workspace)
        projection = ProjectionManager(workspace, registry, event_repo)
        
        provider = MockProvider(workspace)
        orchestrator = AgentOrchestrator(engine, RetryCoordinator(max_attempts=1, base_delay=0), registry, provider)
        recovery = RecoveryEngine(snapshot_repo, event_repo, True)
        runner = WorkflowRunner(engine, orchestrator, projection, recovery)
        
        workflow_id = "wf_e2e"
        engine.snapshot = WorkflowSnapshot(workflow_id=workflow_id, state=WorkflowState.IDEA)
        engine.append_event(WorkflowCreatedEvent(workflow_id=workflow_id))
        engine.transition_state(WorkflowState.DRAFT)
        engine.transition_state(WorkflowState.REVIEW)
        engine.snapshot_repo.save(engine.snapshot)
        
        # We hook into orchestrator to simulate the kill signal
        original_execute = orchestrator.execute_cycle
        def hooked_execute(cycle_id):
            if cycle_id == 2:
                # Kill process by raising exception caught outside
                raise RuntimeError("SIGKILL injected")
            return original_execute(cycle_id)
            
        orchestrator.execute_cycle = hooked_execute
        
        try:
            runner.start_workflow(workflow_id)
        except RuntimeError:
            pass
            
        # Re-initialize everything (simulating resume)
        engine2 = WorkflowEngine(snapshot_repo, event_repo, StateTransitionEngine(), DummyEvaluator())
        registry2 = ArtifactRegistry(workspace)
        projection2 = ProjectionManager(workspace, registry2, event_repo)
        orchestrator2 = AgentOrchestrator(engine2, RetryCoordinator(max_attempts=1, base_delay=0), registry2, provider)
        recovery2 = RecoveryEngine(snapshot_repo, event_repo, True)
        runner2 = WorkflowRunner(engine2, orchestrator2, projection2, recovery2)
        
        # Recover
        recovered_snapshot = recovery2.rehydrate(workflow_id)
        engine2.snapshot = recovered_snapshot
        
        # Resume
        runner2.start_workflow(workflow_id)
        
        assert engine2.snapshot.state == WorkflowState.APPROVED
        
        # Verify artifact
        assert (workspace / "duplicate_finder.py").exists()
        assert (workspace / "test_duplicate_finder.py").exists()
        with open(workspace / "test_duplicate_finder.py", "r") as f:
            content = f.read()
            assert "test_find_duplicates" in content
