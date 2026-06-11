"""Tests for workspace path resolution — CWD independence.

Covers all required scenarios:
  A. cwd = repository root
  B. cwd = repository_root/workspace
  C. cwd = repository_root/src
  D. KARSA_WORKSPACE_DIR set to custom location
  E. Workspace directory does not exist (auto-created)
  F. Workspace directory already exists (preserved)
"""

import os
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from karsa.cli import app
from karsa.workspace.resolver import (
    get_application_root,
    get_diagnostics,
    get_workspace_root,
    resolve_project_workspace,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Unit tests for the resolver module
# ---------------------------------------------------------------------------


class TestWorkspaceResolver:
    """Pure unit tests for workspace.resolver functions."""

    def test_get_workspace_root_default(self, monkeypatch):
        """Default workspace root is <app_root>/workspace."""
        monkeypatch.delenv("KARSA_WORKSPACE_DIR", raising=False)
        root = get_workspace_root()
        expected = get_application_root() / "workspace"
        assert root == expected
        assert root.is_absolute()

    def test_get_workspace_root_env_override(self, tmp_path, monkeypatch):
        """KARSA_WORKSPACE_DIR overrides the default."""
        custom = tmp_path / "my_workspaces"
        monkeypatch.setenv("KARSA_WORKSPACE_DIR", str(custom))
        root = get_workspace_root()
        assert root == custom.resolve()
        assert root.is_absolute()

    def test_resolve_project_workspace(self, monkeypatch):
        """resolve_project_workspace appends the slug to workspace root."""
        monkeypatch.delenv("KARSA_WORKSPACE_DIR", raising=False)
        result = resolve_project_workspace("build-research-vault")
        expected = get_application_root() / "workspace" / "build-research-vault"
        assert result == expected

    def test_resolve_project_workspace_with_env(self, tmp_path, monkeypatch):
        """resolve_project_workspace honours the env var."""
        custom = tmp_path / "custom_ws"
        monkeypatch.setenv("KARSA_WORKSPACE_DIR", str(custom))
        result = resolve_project_workspace("my-project")
        assert result == custom.resolve() / "my-project"

    def test_diagnostics_default(self, monkeypatch):
        """Diagnostics report source='default' when no env var is set."""
        monkeypatch.delenv("KARSA_WORKSPACE_DIR", raising=False)
        diag = get_diagnostics()
        assert diag["source"] == "default"
        assert Path(diag["workspace_root"]).is_absolute()
        assert Path(diag["cwd"]).is_absolute()
        assert Path(diag["application_root"]).is_absolute()

    def test_diagnostics_env(self, tmp_path, monkeypatch):
        """Diagnostics report source=env var name when set."""
        monkeypatch.setenv("KARSA_WORKSPACE_DIR", str(tmp_path))
        diag = get_diagnostics()
        assert diag["source"] == "KARSA_WORKSPACE_DIR"
        assert diag["workspace_root"] == str(tmp_path.resolve())

    def test_workspace_root_is_cwd_independent(self, tmp_path, monkeypatch):
        """Changing CWD must NOT change the resolved workspace root."""
        monkeypatch.delenv("KARSA_WORKSPACE_DIR", raising=False)
        root_from_original_cwd = get_workspace_root()

        # Change CWD to a completely different directory
        monkeypatch.chdir(tmp_path)
        root_from_new_cwd = get_workspace_root()

        assert root_from_original_cwd == root_from_new_cwd


# ---------------------------------------------------------------------------
# Integration tests: CLI commands from various CWDs
# ---------------------------------------------------------------------------


class TestCLICwdIndependence:
    """Integration tests ensuring the CLI works identically from any CWD."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        """Point workspace to a temp dir so tests don't pollute the repo."""
        self.workspace_root = tmp_path / "workspace"
        monkeypatch.setenv("KARSA_WORKSPACE_DIR", str(self.workspace_root))
        monkeypatch.setenv("KARSA_MOCK_LLM", "1")
        yield
        # Cleanup
        if self.workspace_root.exists():
            shutil.rmtree(self.workspace_root)

    def _assert_project_created(self, project_slug: str):
        """Assert that the project workspace was correctly created."""
        project_dir = self.workspace_root / project_slug
        assert project_dir.exists(), f"Project dir not created: {project_dir}"
        assert (project_dir / ".karsa" / "state.json").exists()
        assert (project_dir / "docs").exists()
        assert (project_dir / "src").exists()
        assert (project_dir / ".git").exists()

    def test_scenario_a_cwd_is_repo_root(self, monkeypatch):
        """Scenario A: cwd = repository root."""
        repo_root = get_application_root()
        monkeypatch.chdir(repo_root)

        result = runner.invoke(app, ["start", "--idea", "test scenario a"])
        assert result.exit_code == 0, result.stdout
        assert "Workspace Root:" in result.stdout
        assert "Current Working Directory:" in result.stdout
        self._assert_project_created("test-scenario-a")

    def test_scenario_b_cwd_is_workspace_subdir(self, tmp_path, monkeypatch):
        """Scenario B: cwd = repository_root/workspace (or any subdir)."""
        subdir = tmp_path / "simulated_workspace_subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        result = runner.invoke(app, ["start", "--idea", "test scenario b"])
        assert result.exit_code == 0, result.stdout
        self._assert_project_created("test-scenario-b")

    def test_scenario_c_cwd_is_src_subdir(self, tmp_path, monkeypatch):
        """Scenario C: cwd = repository_root/src."""
        subdir = tmp_path / "simulated_src"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        result = runner.invoke(app, ["start", "--idea", "test scenario c"])
        assert result.exit_code == 0, result.stdout
        self._assert_project_created("test-scenario-c")

    def test_scenario_d_env_override(self, tmp_path, monkeypatch):
        """Scenario D: KARSA_WORKSPACE_DIR set to custom location."""
        custom_root = tmp_path / "my_custom_workspace"
        monkeypatch.setenv("KARSA_WORKSPACE_DIR", str(custom_root))
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["start", "--idea", "test scenario d"])
        assert result.exit_code == 0, result.stdout
        assert (custom_root / "test-scenario-d").exists()
        assert (custom_root / "test-scenario-d" / ".karsa" / "state.json").exists()

    def test_scenario_e_workspace_dir_does_not_exist(self, tmp_path, monkeypatch):
        """Scenario E: Workspace directory does not exist — auto-created."""
        nonexistent = tmp_path / "does_not_exist_yet"
        monkeypatch.setenv("KARSA_WORKSPACE_DIR", str(nonexistent))
        monkeypatch.chdir(tmp_path)

        assert not nonexistent.exists()
        result = runner.invoke(app, ["start", "--idea", "test scenario e"])
        assert result.exit_code == 0, result.stdout
        assert (nonexistent / "test-scenario-e").exists()

    def test_scenario_f_workspace_already_exists_duplicate(self, tmp_path, monkeypatch):
        """Scenario F: Workspace already exists — error preserved."""
        monkeypatch.chdir(tmp_path)

        # First run — should succeed
        result1 = runner.invoke(app, ["start", "--idea", "test scenario f"])
        assert result1.exit_code == 0, result1.stdout

        # Second run — should fail because workspace already exists
        result2 = runner.invoke(app, ["start", "--idea", "test scenario f"])
        assert result2.exit_code == 1
        assert "already exists" in result2.stdout

    def test_cwd_at_tmp(self, monkeypatch):
        """Extra: cwd = /tmp — should still work."""
        monkeypatch.chdir("/tmp")

        result = runner.invoke(app, ["start", "--idea", "test from tmp"])
        assert result.exit_code == 0, result.stdout
        self._assert_project_created("test-from-tmp")


# ---------------------------------------------------------------------------
# Status command diagnostics tests
# ---------------------------------------------------------------------------


class TestStatusDiagnostics:
    """Tests that the status command exposes workspace diagnostics."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        self.workspace_root = tmp_path / "workspace"
        monkeypatch.setenv("KARSA_WORKSPACE_DIR", str(self.workspace_root))
        monkeypatch.setenv("KARSA_MOCK_LLM", "1")
        monkeypatch.chdir(tmp_path)

        # Create a project first
        runner.invoke(app, ["start", "--idea", "status diagnostics test"])
        yield
        if self.workspace_root.exists():
            shutil.rmtree(self.workspace_root)

    def test_status_shows_workspace_root(self):
        result = runner.invoke(app, ["status", "--project", "status-diagnostics-test"])
        assert result.exit_code == 0, result.stdout
        assert "Workspace Root:" in result.stdout

    def test_status_shows_cwd(self):
        result = runner.invoke(app, ["status", "--project", "status-diagnostics-test"])
        assert result.exit_code == 0, result.stdout
        assert "Current Working Directory:" in result.stdout

    def test_status_from_different_cwd(self, tmp_path, monkeypatch):
        """Status must work from any CWD."""
        other_dir = tmp_path / "some_other_dir"
        other_dir.mkdir()
        monkeypatch.chdir(other_dir)

        result = runner.invoke(app, ["status", "--project", "status-diagnostics-test"])
        assert result.exit_code == 0, result.stdout
        assert "Current State:" in result.stdout


# ---------------------------------------------------------------------------
# Draft command CWD independence
# ---------------------------------------------------------------------------


class TestDraftCwdIndependence:
    """Tests that the draft command works from any CWD."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        self.workspace_root = tmp_path / "workspace"
        monkeypatch.setenv("KARSA_WORKSPACE_DIR", str(self.workspace_root))
        monkeypatch.setenv("KARSA_MOCK_LLM", "1")
        monkeypatch.chdir(tmp_path)

        runner.invoke(app, ["start", "--idea", "draft cwd test"])
        yield
        if self.workspace_root.exists():
            shutil.rmtree(self.workspace_root)

    def test_draft_from_repo_root(self, monkeypatch):
        monkeypatch.chdir(get_application_root())
        result = runner.invoke(app, ["draft", "--project", "draft-cwd-test"])
        assert result.exit_code == 0, result.stdout
        assert "Draft artifacts generated" in result.stdout

    def test_draft_from_tmp(self, monkeypatch):
        monkeypatch.chdir("/tmp")
        result = runner.invoke(app, ["draft", "--project", "draft-cwd-test"])
        assert result.exit_code == 0, result.stdout
        assert "Draft artifacts generated" in result.stdout
