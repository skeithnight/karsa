from typer.testing import CliRunner
from karsa.cli import app
from pathlib import Path
import shutil
import pytest

runner = CliRunner()

@pytest.fixture(autouse=True)
def use_temp_workspace(tmp_path, monkeypatch):
    """Point KARSA_WORKSPACE_DIR to a temp directory so tests are isolated
    and CWD-independent."""
    workspace_root = tmp_path / "workspace"
    monkeypatch.setenv("KARSA_WORKSPACE_DIR", str(workspace_root))
    monkeypatch.chdir(tmp_path)
    yield
    # Cleanup after test
    if workspace_root.exists():
        shutil.rmtree(workspace_root)

def test_start_command(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("KARSA_MOCK_LLM", "1")
    
    result = runner.invoke(app, ["start", "--idea", "test"])
    assert result.exit_code == 0
    assert "Starting Karsa with idea" in result.stdout
    assert "Workspace created at" in result.stdout
    assert "Workspace Root:" in result.stdout
    
    workspace = tmp_path / "workspace" / "test"
    assert workspace.exists()
    assert (workspace / ".karsa" / "state.json").exists()
    assert (workspace / "docs").exists()
    assert (workspace / "src").exists()
    assert (workspace / ".git").exists()
    assert (workspace / "docs" / "vision" / "VISION.md").exists()
    assert (workspace / "docs" / "architecture" / "ARCHITECTURE.md").exists()
    assert (workspace / "docs" / "implementation" / "IMPLEMENTATION_PLAN.md").exists()
    assert (workspace / "docs" / "reviews" / "REVIEW_001.md").exists()
    assert (workspace / "docs" / "revisions" / "REVISION_001.md").exists()
    assert (workspace / "docs" / "reviews" / "REVIEW_002.md").exists()

def test_status_command(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("KARSA_MOCK_LLM", "1")
    runner.invoke(app, ["start", "--idea", "build notes app"])
    
    result = runner.invoke(app, ["status", "--project", "build-notes-app"])
    assert result.exit_code == 0
    assert "Current State: APPROVED" in result.stdout
    assert "Provider Health:" in result.stdout
    assert "Current Provider:" in result.stdout
    assert "Workspace Root:" in result.stdout
    assert "Current Working Directory:" in result.stdout

def test_draft_command(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("KARSA_MOCK_LLM", "1")
    runner.invoke(app, ["start", "--idea", "build notes app"])
    
    result = runner.invoke(app, ["draft", "--project", "build-notes-app"])
    assert result.exit_code == 0
    assert "Draft artifacts generated" in result.stdout
    
    workspace = tmp_path / "workspace" / "build-notes-app"
    assert (workspace / "docs" / "vision" / "VISION.md").exists()
    assert (workspace / "docs" / "architecture" / "ARCHITECTURE.md").exists()
    assert (workspace / "docs" / "implementation" / "IMPLEMENTATION_PLAN.md").exists()
