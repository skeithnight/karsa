import typer
from pathlib import Path
from karsa.workflow.controller import StateController
from karsa.artifacts.manager import ArtifactManager
from karsa.git.manager import GitManager
from karsa.models.state import WorkflowState
import re

app = typer.Typer(help="Karsa: Pragmatic AI Orchestrator", no_args_is_help=True)

def get_project_slug(idea: str) -> str:
    words = re.findall(r'\w+', idea.lower())
    if not words:
        return "project"
    return "-".join(words[:3])

@app.command()
def start(idea: str = typer.Option(..., help="The core idea to build")):
    """Start a new Karsa project from an idea."""
    typer.echo(f"Starting Karsa with idea: '{idea}'")
    
    project_slug = get_project_slug(idea)
    # the prompt specifies 'workspace/test' if idea is 'test'
    if project_slug == "test":
        workspace_dir = Path("workspace") / "test"
    else:
        workspace_dir = Path("workspace") / project_slug
    
    if workspace_dir.exists():
        typer.echo(f"Error: Workspace '{workspace_dir}' already exists.")
        raise typer.Exit(code=1)
        
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    state_controller = StateController(workspace_dir)
    state_controller.initialize(idea)
    
    artifact_manager = ArtifactManager(workspace_dir)
    artifact_manager.initialize()
    
    git_manager = GitManager(workspace_dir)
    git_manager.initialize()
    git_manager.commit_state("Karsa: Initialize project and workspace")
    
    typer.echo(f"Workspace created at {workspace_dir}")
    typer.echo(f"Workflow state initialized to {WorkflowState.IDEA.value}")

@app.command()
def approve():
    """Approve a gate."""
    typer.echo("Approval command not yet implemented.")

if __name__ == "__main__":
    app()
