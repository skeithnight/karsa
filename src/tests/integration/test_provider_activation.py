import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

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
from karsa.llm.client import GeminiClient
from karsa.llm.provider import ProviderManager
from karsa.llm.pool import ProviderPool

class DummyEvaluator(GovernanceEvaluator):
    def evaluate(self, snapshot, ex_id, rev_id):
        return GovernanceDecision(workflow_id=snapshot.workflow_id, review_cycle_id=rev_id, execution_id=ex_id, sequence_number=0, decision_type="ALLOW", reason="Default")

def create_mock_response(text: str):
    mock_resp = MagicMock()
    mock_resp.text = text
    return mock_resp

def test_real_provider_activation():
    import os
    use_mock = not bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or os.environ.get("KARSA_GEMINI_KEYS"))

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        registry_file = workspace / ".karsa" / "providers.json"
        
        # Real Provider Setup (ProviderPool will self-resolve)
        pool = ProviderPool("gemini", [], registry_file)
        
        if use_mock:
            # Inject dummy key so tests can proceed without network
            pool = ProviderPool("gemini", ["dummy_key"], registry_file)
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
        
        workflow_id = "wf_provider_test"
        engine.snapshot = WorkflowSnapshot(workflow_id=workflow_id, state=WorkflowState.IDEA)
        engine.append_event(WorkflowCreatedEvent(workflow_id=workflow_id))
        engine.transition_state(WorkflowState.DRAFT)
        engine.transition_state(WorkflowState.REVIEW)
        engine.snapshot_repo.save(engine.snapshot)
        
        original_execute = orchestrator.execute_cycle
        def hooked_execute(cycle_id):
            if cycle_id == 2:
                # We only want to run 1 full cycle to prove connectivity
                raise RuntimeError("Workflow Cycle 1 Completed")
            return original_execute(cycle_id)
        
        orchestrator.execute_cycle = hooked_execute
        
        def run_test():
            try:
                runner.start_workflow(workflow_id)
            except RuntimeError as e:
                if str(e) == "Workflow Cycle 1 Completed":
                    pass
                else:
                    raise e

        if use_mock:
            import sys
            mock_google = MagicMock()
            sys.modules["google"] = mock_google
            sys.modules["google.genai"] = mock_google.genai
            
            with patch("google.genai.Client") as MockGoogleClient:
                mock_client_instance = MagicMock()
                MockGoogleClient.return_value = mock_client_instance
                
                # Mock PE response then Review response
                mock_client_instance.models.generate_content.side_effect = [
                    create_mock_response("```python\n# calculator\nprint('hello')\n```"),
                    create_mock_response('{"decision": "APPROVED", "convergence_score": 1.0, "blocking_issues": []}')
                ]
                run_test()
                assert mock_client_instance.models.generate_content.call_count == 2
        else:
            run_test()

        # Evidence Checks
        events = event_repo.load(workflow_id)
        artifacts_persisted = [e for e in events if type(e).__name__ == "ArtifactPersistedEvent"]
        
        assert len(artifacts_persisted) >= 2
        
        # Verify provider usage statistics
        assert pool.keys[0].total_requests >= 2
        assert provider_manager.model_name == "gemini-2.5-flash"
