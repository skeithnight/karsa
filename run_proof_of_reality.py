import os
import sys
import tempfile
from pathlib import Path

from karsa.domain.persistence import SnapshotRepository, EventJournalRepository
from karsa.domain.models import WorkflowState, WorkflowSnapshot
from karsa.domain.events import WorkflowCreatedEvent, ArtifactPersistedEvent
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
from karsa.llm.client import GeminiClient
from karsa.llm.provider import ProviderManager
from karsa.llm.pool import ProviderPool

class DummyEvaluator(GovernanceEvaluator):
    def evaluate(self, snapshot, ex_id, rev_id):
        return GovernanceDecision(workflow_id=snapshot.workflow_id, review_cycle_id=rev_id, execution_id=ex_id, sequence_number=0, decision_type="ALLOW", reason="Default")

def run():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        registry_file = workspace / ".karsa" / "providers.json"
        
        pool = ProviderPool("gemini", [], registry_file)
        gemini_client = GeminiClient(obs_manager=None, pool=pool)
        provider_manager = ProviderManager(providers=[gemini_client])
        
        snapshot_repo = SnapshotRepository(workspace)
        event_repo = EventJournalRepository(workspace)
        engine = WorkflowEngine(snapshot_repo, event_repo, StateTransitionEngine(), DummyEvaluator())
        registry = ArtifactRegistry(workspace)
        projection = ProjectionManager(workspace, registry, event_repo)
        
        orchestrator = AgentOrchestrator(engine, RetryCoordinator(max_attempts=1, base_delay=0), registry, provider_manager)
        recovery = RecoveryEngine(snapshot_repo, event_repo, True)
        runner = WorkflowRunner(engine, orchestrator, projection, recovery)
        
        workflow_id = "wf_reality_001"
        engine.snapshot = WorkflowSnapshot(workflow_id=workflow_id, state=WorkflowState.IDEA)
        engine.append_event(WorkflowCreatedEvent(workflow_id=workflow_id))
        engine.transition_state(WorkflowState.DRAFT)
        engine.transition_state(WorkflowState.REVIEW)
        engine.snapshot_repo.save(engine.snapshot)
        
        # Override the objective specifically for this proof
        original_execute = orchestrator.execute_cycle
        def hooked_execute(cycle_id):
            orchestrator.objective = "Create a Python function add(a, b) and a pytest test validating add(2,3)==5"
            return original_execute(cycle_id)
            
        orchestrator.execute_cycle = hooked_execute
        
        runner.start_workflow(workflow_id)
        
        # Gather evidence
        generated_code = ""
        with open(workspace / "duplicate_finder.py", "r") as f:
            generated_code = f.read()
            
        events = event_repo.load(workflow_id)
        
        # Re-run pytest manually to capture output for proof
        tool_output = orchestrator.tool_executor.run_pytest(workspace)
        
        proof_content = f"""# Proof of Reality

## Workflow Context
- **Workflow ID:** {workflow_id}
- **Provider:** {provider_manager.model_name}
- **Final FSM State:** {engine.snapshot.state.name}

## Generated Artifact
```python
{generated_code}
```

## Pytest Output
```text
{tool_output}
```

## State Transitions
"""
        for e in events:
            if type(e).__name__ == "StateTransitionedEvent":
                proof_content += f"- {e.previous_state.name} -> {e.new_state.name}\n"
                
        with open("proof_of_reality.md", "w") as f:
            f.write(proof_content)
        
        print("Proof of reality generated at proof_of_reality.md")

if __name__ == "__main__":
    run()
