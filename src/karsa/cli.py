import typer
from pathlib import Path
from karsa.workflow.controller import StateController
from karsa.artifacts.manager import ArtifactManager
from karsa.git.manager import GitManager
from karsa.models.state import WorkflowState
from karsa.workspace.resolver import (
    resolve_project_workspace,
    get_workspace_root,
    get_diagnostics,
)
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
    
    # Log workspace diagnostics at startup
    diag = get_diagnostics()
    typer.echo(f"Workspace Root: {diag['workspace_root']}")
    typer.echo(f"Current Working Directory: {diag['cwd']}")
    
    project_slug = get_project_slug(idea)
    workspace_dir = resolve_project_workspace(project_slug)
    
    if workspace_dir.exists():
        typer.echo(f"Error: Workspace '{workspace_dir}' already exists.")
        raise typer.Exit(code=1)
        
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    from karsa.observability.manager import ObservabilityManager
    obs_manager = ObservabilityManager(workspace_dir)
    obs_manager.log_trace("WorkflowStarted")
    obs_manager.log_trace(f"WorkspaceRoot={diag['workspace_root']}")
    obs_manager.log_trace(f"CWD={diag['cwd']}")
    obs_manager.log_trace(f"WorkspaceSource={diag['source']}")

    state_controller = StateController(workspace_dir)
    state_controller.initialize(idea)
    
    artifact_manager = ArtifactManager(workspace_dir, obs_manager=obs_manager)
    artifact_manager.initialize()
    
    git_manager = GitManager(workspace_dir)
    git_manager.initialize()
    git_manager.commit_state("Karsa: Initialize project and workspace")
    
    typer.echo(f"Workspace created at {workspace_dir}")
    typer.echo(f"Workflow state initialized to {WorkflowState.IDEA.value}")
    
    typer.echo("Drafting initial design with ProductEngineerAgent...")
    import os
    from karsa.llm.client import MockLLMClient, GeminiClient
    from karsa.agents.product_engineer import ProductEngineerAgent
    from karsa.agents.review_agent import ReviewAgent
    from karsa.llm.provider import ProviderManager
    from karsa.llm.pool import ProviderPool
    
    allow_mock = os.environ.get("KARSA_ENV") == "test" or os.environ.get("KARSA_MOCK_LLM") == "1"
    keys_env = os.environ.get("KARSA_GEMINI_KEYS", "")
    if keys_env:
        gemini_keys = [k.strip() for k in keys_env.split(",") if k.strip()]
    else:
        gemini_keys = [os.environ.get("GEMINI_API_KEY")] if os.environ.get("GEMINI_API_KEY") else []
        
    providers = []
    registry_file = workspace_dir / ".karsa" / "provider_registry.json"
    
    if gemini_keys:
        pool1 = ProviderPool("gemini-2.5-flash", gemini_keys, registry_file, trace_fn=obs_manager.log_trace)
        gemini_client = GeminiClient(obs_manager=obs_manager, pool=pool1)
        
        pool2 = ProviderPool("gemini-2.5-flash-lite", gemini_keys, registry_file, trace_fn=obs_manager.log_trace)
        gemini_lite_client = GeminiClient(obs_manager=obs_manager, pool=pool2)
        gemini_lite_client.model_name = "gemini-2.5-flash-lite"
        
        providers.extend([gemini_client, gemini_lite_client])
        typer.echo(f"Using Gemini Fallback Chain with {len(gemini_keys)} keys.")
        
    if allow_mock:
        mock_client = MockLLMClient(obs_manager=obs_manager)
        providers.append(mock_client)
        typer.echo("Mock LLM enabled in fallback chain.")
        
    if not providers:
        typer.echo("Error: No providers configured. Provide KARSA_GEMINI_KEYS or enable KARSA_MOCK_LLM=1")
        raise typer.Exit(code=1)
        
    llm_client = ProviderManager(providers=providers, obs_manager=obs_manager)
        
    pe_agent = ProductEngineerAgent(llm_client, artifact_manager)
    try:
        pe_agent.draft_design(idea)
    except Exception as e:
        typer.echo(f"Critical Failure: {str(e)}")
        if "429 QUOTA" in str(e).upper() or "ALL PROVIDERS FAILED" in str(e).upper():
            state_controller.transition_to(WorkflowState.AWAITING_PROVIDER)
            git_manager.commit_state("Karsa: Workflow paused awaiting provider capacity")
        else:
            state_controller.transition_to(WorkflowState.FAILED)
            git_manager.commit_state("Karsa: Workflow FAILED due to provider failure")
        return
    
    state_controller.transition_to(WorkflowState.DRAFT)
    git_manager.commit_state("Karsa: Drafted Vision, Architecture, and Implementation Plan")
    typer.echo("Product Engineer artifacts generated successfully.")
    
    from karsa.workflow.engine import RevisionEngine
    from karsa.review.registry import IssueRegistry
    from karsa.review.convergence import ReviewConvergenceEngine
    
    issue_registry = IssueRegistry(workspace_dir)
    convergence_engine = ReviewConvergenceEngine(issue_registry)
    
    review_agent = ReviewAgent(llm_client, artifact_manager)
    engine = RevisionEngine(state_controller, artifact_manager, git_manager, pe_agent, review_agent, issue_registry, convergence_engine, obs_manager)
    engine.run_loop()

@app.command()
def status(project: str = typer.Option(..., help="The project to check")):
    """Check the status of a project."""
    workspace_dir = resolve_project_workspace(project)
    if not workspace_dir.exists():
        typer.echo(f"Error: Project '{project}' not found.")
        raise typer.Exit(code=1)
        
    state_controller = StateController(workspace_dir)
    state = state_controller.load_state()
    current_state = state.get("current_state", "UNKNOWN")
    
    # Read authoritative cycle and decision from state.json
    current_cycle = state.get("current_cycle", 0)
    latest_decision = state.get("latest_decision", "NONE")
    open_blocking = state.get("open_blocking_issues", 0)
    open_non_blocking = state.get("open_non_blocking_issues", 0)
    resolved_issues = state.get("resolved_issues", 0)
    
    from karsa.observability.manager import ObservabilityManager
    obs_manager = ObservabilityManager(workspace_dir)
    info = obs_manager.get_status_info()
    
    # Workspace diagnostics
    diag = get_diagnostics()
    typer.echo(f"Workspace Root: {diag['workspace_root']}")
    typer.echo(f"Current Working Directory: {diag['cwd']}")
    typer.echo("")

    typer.echo(f"Project: {project}")
    typer.echo(f"Current State: {current_state}")
    typer.echo("")
    typer.echo(f"Current Cycle: {current_cycle}")
    typer.echo("")
    typer.echo(f"Open Blocking Issues: {open_blocking}")
    typer.echo(f"Open Non Blocking Issues: {open_non_blocking}")
    typer.echo("")
    typer.echo(f"Resolved Issues: {resolved_issues}")
    typer.echo("")
    typer.echo(f"Latest Decision: {latest_decision}")
    typer.echo("")
    typer.echo(f"Model: {info['current_model']}")
    typer.echo("")
    typer.echo(f"Provider Health:")
    typer.echo(f"{info['provider_health']}")
    typer.echo("")
    typer.echo(f"Current Provider:")
    typer.echo(f"{info['current_provider']}")
    typer.echo("")
    typer.echo(f"Current Key:")
    typer.echo(f"{info.get('current_key', 'none')}")
    typer.echo("")
    typer.echo(f"Retry Count:")
    typer.echo(f"{info['retry_count']}")
    typer.echo("")
    typer.echo(f"Fallback Count:")
    typer.echo(f"{info['fallback_count']}")
    typer.echo("")
    typer.echo(f"Quota Failures:")
    typer.echo(f"{info.get('quota_failures', 0)}")
    typer.echo("")
    typer.echo(f"Last Error:")
    typer.echo(f"{info['last_error']}")
    typer.echo("")
    typer.echo(f"Last Failure Timestamp:")
    typer.echo(f"{info.get('last_failure_timestamp', 'N/A')}")
    typer.echo("")
    typer.echo(f"Execution Count: {info['execution_count']}")
    typer.echo("")
    typer.echo(f"Total Runtime: {info['total_runtime']} ms")
    typer.echo("")
    typer.echo(f"Last Activity Timestamp: {info['last_activity']}")
    typer.echo("")
    typer.echo(f"Convergence Trend: {info['convergence_score']}")

    # Parser diagnostics
    parser_debug_file = workspace_dir / ".karsa" / "parser_debug.json"
    if parser_debug_file.exists():
        import json as json_mod
        with open(parser_debug_file, "r") as f:
            parser_debug = json_mod.load(f)
        typer.echo("")
        typer.echo("--- Parser Diagnostics ---")
        typer.echo(f"Parsed Review Outcome: {parser_debug.get('detected_outcome', 'N/A')}")
        typer.echo(f"Parsed Blocking Count: {parser_debug.get('extracted_new_blocking', 'N/A')}")
        typer.echo(f"Parsed Non Blocking Count: {parser_debug.get('extracted_new_non_blocking', 'N/A')}")
        typer.echo(f"Parser Confidence: {parser_debug.get('confidence', 'N/A')}")
        warnings = parser_debug.get('parse_warnings', [])
        if warnings:
            typer.echo(f"Parser Warnings: {'; '.join(warnings)}")
        else:
            typer.echo("Parser Warnings: None")
    else:
        typer.echo("")
        typer.echo("--- Parser Diagnostics ---")
        typer.echo("No parser diagnostics available (no reviews processed yet).")

@app.command()
def draft(project: str = typer.Option(..., help="The project to draft")):
    """Draft static templates for the project."""
    workspace_dir = resolve_project_workspace(project)
    if not workspace_dir.exists():
        typer.echo(f"Error: Project '{project}' not found.")
        raise typer.Exit(code=1)
        
    artifact_manager = ArtifactManager(workspace_dir)
    
    vision_content = "# Vision\n\nThis is the static template for the vision."
    arch_content = "# Architecture\n\nThis is the static template for architecture."
    impl_content = "# Implementation Plan\n\nThis is the static template for the implementation plan."
    
    artifact_manager.write_artifact("docs/vision/VISION.md", vision_content)
    artifact_manager.write_artifact("docs/architecture/ARCHITECTURE.md", arch_content)
    artifact_manager.write_artifact("docs/implementation/IMPLEMENTATION_PLAN.md", impl_content)
    
    typer.echo(f"Draft artifacts generated for project '{project}'")

@app.command()
def approve():
    """Approve a gate."""
    typer.echo("Approval command not yet implemented.")

if __name__ == "__main__":
    app()
