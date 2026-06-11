from typer.testing import CliRunner
from karsa.cli import app
from pathlib import Path
import shutil
import pytest

runner = CliRunner()

@pytest.fixture(autouse=True)
def clean_workspace():
    yield
    # Cleanup after test
    workspace = Path("workspace")
    if workspace.exists():
        shutil.rmtree(workspace)

def test_start_command(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    
    result = runner.invoke(app, ["start", "--idea", "test"])
    assert result.exit_code == 0
    assert "Starting Karsa with idea" in result.stdout
    assert "Workspace created at workspace/test" in result.stdout
    
    workspace = tmp_path / "workspace" / "test"
    assert workspace.exists()
    assert (workspace / ".karsa" / "state.json").exists()
    assert (workspace / "docs").exists()
    assert (workspace / "src").exists()
    assert (workspace / ".git").exists()
