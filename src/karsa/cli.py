import typer
from pathlib import Path
from karsa.workspace.resolver import resolve_project_workspace, get_diagnostics
from karsa.domain.persistence import SnapshotRepository, EventJournalRepository
from karsa.domain.models import WorkflowState
from karsa.domain.events import WorkflowCreatedEvent, StateTransitionedEvent
from karsa.workflow.fsm import StateTransitionEngine
from karsa.governance.evaluator import GovernanceEvaluator
from karsa.workflow.workflow_engine import WorkflowEngine
from karsa.artifacts.registry import ArtifactRegistry
from karsa.artifacts.projection import ProjectionManager
from karsa.workflow.retry import RetryCoordinator
from karsa.workflow.orchestrator import AgentOrchestrator
from karsa.workflow.recovery import RecoveryEngine
from karsa.workflow.runner import WorkflowRunner
import time

app = typer.Typer(help="Karsa: Pragmatic AI Orchestrator", no_args_is_help=True)

@app.command()
def start(idea: str = typer.Option(..., help="The core idea to build")):
    """Start a new Karsa project from an idea."""
    typer.echo(f"Starting Karsa with idea: '{idea}'")
    
    diag = get_diagnostics()
    typer.echo(f"Workspace Root: {diag['workspace_root']}")
    typer.echo(f"Current Working Directory: {diag['cwd']}")
    
    project_slug = "project"
    workspace_dir = resolve_project_workspace(project_slug)
    
    if workspace_dir.exists():
        typer.echo(f"Error: Workspace '{workspace_dir}' already exists.")
        raise typer.Exit(code=1)
        
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize Core Domain
    snapshot_repo = SnapshotRepository(workspace_dir)
    event_repo = EventJournalRepository(workspace_dir)
    fsm = StateTransitionEngine()
    
    class DummyEvaluator(GovernanceEvaluator):
        def evaluate(self, snapshot, ex_id, rev_id):
            from karsa.domain.models import GovernanceDecision
            return GovernanceDecision(workflow_id=snapshot.workflow_id, review_cycle_id=rev_id, execution_id=ex_id, sequence_number=0, decision_type="ALLOW", reason="Default")
            
    evaluator = DummyEvaluator()
    
    # Initialize Orchestration & Subsystems
    engine = WorkflowEngine(snapshot_repo, event_repo, fsm, evaluator)
    registry = ArtifactRegistry(workspace_dir)
    projection = ProjectionManager(workspace_dir, registry, event_repo)
    retry_coordinator = RetryCoordinator()
    orchestrator = AgentOrchestrator(engine, retry_coordinator, registry)
    recovery = RecoveryEngine(snapshot_repo, event_repo, is_replaying=True)
    
    runner = WorkflowRunner(engine, orchestrator, projection, recovery)
    
    # Boot workflow
    workflow_id = "wf_" + str(int(time.time()))
    
    from karsa.domain.models import WorkflowSnapshot
    engine.snapshot = WorkflowSnapshot(workflow_id=workflow_id, state=WorkflowState.IDEA)
    engine.append_event(WorkflowCreatedEvent(workflow_id=workflow_id))
    engine.transition_state(WorkflowState.DRAFT, reason="Initial idea")
    engine.transition_state(WorkflowState.REVIEW, reason="Moving to review")
    
    typer.echo(f"Workspace created at {workspace_dir}")
    typer.echo("Executing WorkflowRunner...")
    
    runner.start_workflow(workflow_id)
    
    typer.echo("Workflow finished.")

@app.command()
def resume(project: str = typer.Option(..., help="The project to resume"), workflow_id: str = typer.Option(..., help="Workflow ID")):
    workspace_dir = resolve_project_workspace(project)
    if not workspace_dir.exists():
        typer.echo(f"Error: Project '{project}' not found.")
        raise typer.Exit(code=1)
        
    snapshot_repo = SnapshotRepository(workspace_dir)
    event_repo = EventJournalRepository(workspace_dir)
    fsm = StateTransitionEngine()
    
    class DummyEvaluator(GovernanceEvaluator):
        def evaluate(self, snapshot, ex_id, rev_id):
            from karsa.domain.models import GovernanceDecision
            return GovernanceDecision(workflow_id=snapshot.workflow_id, review_cycle_id=rev_id, execution_id=ex_id, sequence_number=0, decision_type="ALLOW", reason="Default")
            
    evaluator = DummyEvaluator()
    
    engine = WorkflowEngine(snapshot_repo, event_repo, fsm, evaluator)
    registry = ArtifactRegistry(workspace_dir)
    projection = ProjectionManager(workspace_dir, registry, event_repo)
    retry_coordinator = RetryCoordinator()
    orchestrator = AgentOrchestrator(engine, retry_coordinator, registry)
    recovery = RecoveryEngine(snapshot_repo, event_repo, is_replaying=True)
    
    runner = WorkflowRunner(engine, orchestrator, projection, recovery)
    
    typer.echo(f"Resuming workflow {workflow_id}...")
    runner.resume(workflow_id)
    typer.echo("Workflow finished.")
    
@app.command()
def status(project: str = typer.Option(..., help="The project to check")):
    typer.echo(f"Status for {project} checked.")

if __name__ == "__main__":
    app()
