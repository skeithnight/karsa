import pytest
import os
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from karsa.domain.persistence import SnapshotRepository, EventJournalRepository
from karsa.domain.models import WorkflowState, WorkflowSnapshot
from karsa.domain.events import WorkflowCreatedEvent, ArtifactPersistedEvent, ExecutionCheckpointEvent
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
from karsa.llm.client import LLMClient

class MockMockProvider(LLMClient):
    def __init__(self, mode="success"):
        self.mode = mode
        self.call_count = 0
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        self.call_count += 1
        if "Product Engineer" in prompt:
            return """
<file path="src/main.py">
print("main")
</file>
<file path="src/service.py">
print("service")
</file>
<file path="tests/test_service.py">
def test_svc(): pass
</file>
"""
        elif "Review Agent" in prompt:
            return '{"decision": "APPROVED", "convergence_score": 1.0, "blocking_issues": []}'
        return ""

class DummyEvaluator(GovernanceEvaluator):
    def evaluate(self, snapshot, ex_id, rev_id):
        return GovernanceDecision(workflow_id=snapshot.workflow_id, review_cycle_id=rev_id, execution_id=ex_id, sequence_number=0, decision_type="ALLOW", reason="Default")

def setup_workflow(workspace):
    snapshot_repo = SnapshotRepository(workspace)
    event_repo = EventJournalRepository(workspace)
    engine = WorkflowEngine(snapshot_repo, event_repo, StateTransitionEngine(), DummyEvaluator())
    registry = ArtifactRegistry(workspace)
    projection = ProjectionManager(workspace, registry, event_repo)
    
    provider = MockMockProvider()
    orchestrator = AgentOrchestrator(engine, RetryCoordinator(max_attempts=1, base_delay=0), registry, provider)
    recovery = RecoveryEngine(snapshot_repo, event_repo, True)
    runner = WorkflowRunner(engine, orchestrator, projection, recovery)
    
    return engine, orchestrator, runner, event_repo, registry

def test_multifile_crash_recovery():
    with TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        engine, orchestrator, runner, event_repo, registry = setup_workflow(workspace)
        
        workflow_id = "wf_multi_001"
        engine.snapshot = WorkflowSnapshot(workflow_id=workflow_id, state=WorkflowState.IDEA)
        engine.append_event(WorkflowCreatedEvent(workflow_id=workflow_id))
        engine.transition_state(WorkflowState.DRAFT)
        engine.transition_state(WorkflowState.REVIEW)
        engine.snapshot_repo.save(engine.snapshot)
        
        # Inject crash during file persist
        original_append = engine.append_event
        crash_count = [0]
        
        def hooked_append(event):
            if isinstance(event, ArtifactPersistedEvent) and event.target_path == "src/service.py":
                crash_count[0] += 1
                if crash_count[0] == 1:
                    original_append(event)
                    raise KeyboardInterrupt("Simulated Crash after partial file set")
            original_append(event)
            
        engine.append_event = hooked_append
        
        try:
            runner.start_workflow(workflow_id)
        except KeyboardInterrupt as e:
            assert "Simulated Crash after partial file set" in str(e)
            
        # Verify state: main.py and service.py events should exist, but NO manifest checkpoint
        events = event_repo.load(workflow_id)
        persisted = [e for e in events if isinstance(e, ArtifactPersistedEvent)]
        assert len(persisted) == 2
        assert persisted[0].target_path == "src/main.py"
        assert persisted[1].target_path == "src/service.py"
        
        checkpoints = [e for e in events if isinstance(e, ExecutionCheckpointEvent) and e.sub_task_name == "PE_COMPLETE"]
        assert len(checkpoints) == 0
        
        # Now recover and run to completion
        engine2, orchestrator2, runner2, event_repo2, registry2 = setup_workflow(workspace)
        
        original_execute = orchestrator2.execute_cycle
        def hook_cycle(cycle_id):
            if cycle_id == 2:
                raise RuntimeError("Workflow Cycle 1 Completed")
            return original_execute(cycle_id)
            
        orchestrator2.execute_cycle = hook_cycle
        
        try:
            runner2.start_workflow(workflow_id)
        except RuntimeError as e:
            if "Workflow Cycle 1 Completed" not in str(e):
                raise e
                
        # Validate multi-file outputs
        assert (workspace / "src/main.py").exists()
        assert (workspace / "src/service.py").exists()
        assert (workspace / "tests/test_service.py").exists()
        
        # Validate manifest checkpoint exists
        events2 = event_repo2.load(workflow_id)
        checkpoints2 = [e for e in events2 if isinstance(e, ExecutionCheckpointEvent) and e.sub_task_name == "PE_COMPLETE"]
        assert len(checkpoints2) == 1
        
        manifest_hash = checkpoints2[0].artifact_version_hash
        manifest_str = registry2.get_versioned(manifest_hash)
        manifest = json.loads(manifest_str)
        assert manifest["version"] == 1
        assert "src/main.py" in manifest["files"]
        assert "src/service.py" in manifest["files"]
        assert "tests/test_service.py" in manifest["files"]
        
        # Verify Review context was restricted appropriately
        # (This is implicitly tested by the prompt building logic executing without error during the cycle)
        # We can also check that orchestrator2.provider.call_count is 2 (1 for PE, 1 for Review)
        assert orchestrator2.provider.call_count == 2
