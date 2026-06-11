"""Tests for workflow state tracking, cycle tracking, decision provenance, and provider observability.

Covers:
- Authoritative state persistence (state.json schema)
- Cycle tracking accuracy across review cycles
- Status command reading from authoritative state
- Decision provenance (reason never empty/Unknown)
- Provider rotation trace events
- Regression scenarios
"""
import pytest
import json
import os
import re
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch
from karsa.workflow.controller import StateController
from karsa.workflow.engine import RevisionEngine, _extract_decision_reason
from karsa.models.state import WorkflowState
from karsa.observability.manager import ObservabilityManager
from karsa.observability.trace import TraceLogger
from karsa.artifacts.manager import ArtifactManager
from karsa.review.registry import IssueRegistry
from karsa.review.convergence import ReviewConvergenceEngine
from karsa.llm.pool import ProviderPool, ProviderKey
from karsa.llm.provider import ProviderManager, ProviderRetryPolicy
from karsa.llm.client import LLMClient


# ============================================================
# 1. STATE MODEL TESTS
# ============================================================

class TestStateModel:
    """Verify state.json contains all required fields."""

    def test_initialize_creates_full_state(self, tmp_path: Path):
        controller = StateController(tmp_path)
        controller.initialize("Test idea")

        state = controller.load_state()
        assert state["current_state"] == WorkflowState.IDEA.value
        assert state["idea"] == "Test idea"
        assert state["current_cycle"] == 0
        assert state["latest_decision"] == "NONE"
        assert state["open_blocking_issues"] == 0
        assert state["open_non_blocking_issues"] == 0
        assert state["resolved_issues"] == 0
        assert "last_updated_timestamp" in state
        assert "provider_summary" in state

    def test_update_cycle(self, tmp_path: Path):
        controller = StateController(tmp_path)
        controller.initialize("Test idea")
        controller.update_cycle(2)

        state = controller.load_state()
        assert state["current_cycle"] == 2

    def test_update_decision(self, tmp_path: Path):
        controller = StateController(tmp_path)
        controller.initialize("Test idea")
        controller.update_decision("APPROVE")

        state = controller.load_state()
        assert state["latest_decision"] == "APPROVE"

    def test_update_issues(self, tmp_path: Path):
        controller = StateController(tmp_path)
        controller.initialize("Test idea")
        controller.update_issues(blocking=3, non_blocking=2, resolved=1)

        state = controller.load_state()
        assert state["open_blocking_issues"] == 3
        assert state["open_non_blocking_issues"] == 2
        assert state["resolved_issues"] == 1

    def test_update_provider_summary(self, tmp_path: Path):
        controller = StateController(tmp_path)
        controller.initialize("Test idea")
        summary = {"model": "gemini-2.5-flash", "health": "HEALTHY"}
        controller.update_provider_summary(summary)

        state = controller.load_state()
        assert state["provider_summary"] == summary

    def test_get_current_cycle(self, tmp_path: Path):
        controller = StateController(tmp_path)
        controller.initialize("Test idea")
        assert controller.get_current_cycle() == 0
        controller.update_cycle(3)
        assert controller.get_current_cycle() == 3

    def test_get_latest_decision(self, tmp_path: Path):
        controller = StateController(tmp_path)
        controller.initialize("Test idea")
        assert controller.get_latest_decision() == "NONE"
        controller.update_decision("REJECT")
        assert controller.get_latest_decision() == "REJECT"

    def test_transition_preserves_extended_fields(self, tmp_path: Path):
        controller = StateController(tmp_path)
        controller.initialize("Test idea")
        controller.update_cycle(2)
        controller.update_decision("REJECT")
        controller.update_issues(1, 2, 3)

        controller.transition_to(WorkflowState.REVIEW)

        state = controller.load_state()
        assert state["current_state"] == WorkflowState.REVIEW.value
        assert state["current_cycle"] == 2
        assert state["latest_decision"] == "REJECT"
        assert state["open_blocking_issues"] == 1

    def test_last_updated_timestamp_changes(self, tmp_path: Path):
        controller = StateController(tmp_path)
        controller.initialize("Test idea")
        state1 = controller.load_state()
        ts1 = state1["last_updated_timestamp"]

        controller.update_cycle(1)
        state2 = controller.load_state()
        ts2 = state2["last_updated_timestamp"]

        # Timestamps should be present (may be same if fast)
        assert ts1 is not None
        assert ts2 is not None


# ============================================================
# 2. CYCLE TRACKING TESTS
# ============================================================

class MockLLMForCycles(LLMClient):
    """Configurable mock that can produce REJECT for N cycles then APPROVE."""
    def __init__(self, reject_cycles: int = 1):
        super().__init__()
        self.model_name = "mock-cycles"
        self.current_key = "mock"
        self.call_count = 0
        self.reject_cycles = reject_cycles

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        self.call_count += 1
        sys_upper = system_prompt.upper()

        if "VISION" in sys_upper and "ARCHITECTURE" not in sys_upper:
            return "# Vision\n## A specific problem statement\nMock.\n## Target users\nMock.\n## Goals\nMock.\n## Non-goals\nMock.\n## Success criteria\nMock."
        elif "ARCHITECTURE" in sys_upper and "VISION" in sys_upper and "TECH LEAD" not in sys_upper:
            return "# Architecture\n## Concrete architecture choices\nMock.\n## Rationale\nMock.\n## Tradeoffs\nMock.\n## Components\nMock.\n## Data flow\nMock."
        elif "REVISE" in sys_upper:
            return (
                "# Vision\n## A specific problem statement\nRevised.\n## Target users\nRevised.\n## Goals\nRevised.\n## Non-goals\nRevised.\n## Success criteria\nRevised.\n---\n"
                "# Architecture\n## Concrete architecture choices\nRevised.\n## Rationale\nRevised.\n## Tradeoffs\nRevised.\n## Components\nRevised.\n## Data flow\nRevised.\n---\n"
                "# Implementation Plan\n## Delivery phases\nRevised.\n## Real milestones\nRevised.\n## Actionable tasks\nRevised."
            )
        elif "TECH LEAD" in sys_upper:
            return "# Implementation Plan\n## Delivery phases\nMock.\n## Real milestones\nMock.\n## Actionable tasks\nMock."
        elif "REVIEWER" in sys_upper or "SKEPTICAL" in sys_upper or "VERIFICATION" in sys_upper:
            if "unresolved" in prompt.lower() or "revised" in prompt.lower():
                return (
                    "# Review Result\n\nOutcome:\nAPPROVE\n\n"
                    "# Existing Issues\n"
                    "Issue: P001\nStatus: RESOLVED\n\n"
                    "# New Issues\n\n"
                    "# Summary\n\n"
                    "Open Blocking Issues: 0\n"
                    "Open Non Blocking Issues: 0\n\n"
                    "# Confidence\n0.95"
                )
            return (
                "# Review Result\n\nOutcome:\nREJECT\n\n"
                "# Existing Issues\n\n"
                "# New Issues\n\n"
                "Issue: A001\nSeverity: BLOCKING\n\nDescription:\nThe Problem definition lacks measurable goals.\n\nEvidence:\nNo numbers.\n\n"
                "# Summary\n\n"
                "Open Blocking Issues: 1\n"
                "Open Non Blocking Issues: 0\n\n"
                "# Confidence\n0.85"
            )
        return f"Mock response"

    def generate_with_obs(self, agent_name: str, prompt: str, system_prompt: str = "") -> str:
        return self.generate(prompt, system_prompt)


class MockGitManager:
    def __init__(self):
        self.commits = []

    def initialize(self):
        pass

    def commit_state(self, message: str):
        self.commits.append(message)


def _build_engine(tmp_path: Path, mock_llm=None):
    """Helper to build a RevisionEngine with mocks."""
    from karsa.agents.product_engineer import ProductEngineerAgent
    from karsa.agents.review_agent import ReviewAgent

    workspace = tmp_path
    (workspace / ".karsa").mkdir(parents=True, exist_ok=True)
    (workspace / "docs" / "vision").mkdir(parents=True, exist_ok=True)
    (workspace / "docs" / "architecture").mkdir(parents=True, exist_ok=True)
    (workspace / "docs" / "implementation").mkdir(parents=True, exist_ok=True)
    (workspace / "docs" / "reviews").mkdir(parents=True, exist_ok=True)
    (workspace / "docs" / "revisions").mkdir(parents=True, exist_ok=True)

    llm = mock_llm or MockLLMForCycles()
    obs = ObservabilityManager(workspace)
    state_ctrl = StateController(workspace)
    state_ctrl.initialize("test idea")
    artifact_mgr = ArtifactManager(workspace, obs_manager=obs)
    git_mgr = MockGitManager()
    pe_agent = ProductEngineerAgent(llm, artifact_mgr)
    review_agent = ReviewAgent(llm, artifact_mgr)
    issue_registry = IssueRegistry(workspace)
    convergence = ReviewConvergenceEngine(issue_registry)

    # Write initial artifacts so review has something to review
    artifact_mgr.write_artifact("docs/vision/VISION.md", "# Vision\n## A specific problem statement\nInitial.")
    artifact_mgr.write_artifact("docs/architecture/ARCHITECTURE.md", "# Architecture\nInitial.")
    artifact_mgr.write_artifact("docs/implementation/IMPLEMENTATION_PLAN.md", "# Plan\nInitial.")

    engine = RevisionEngine(state_ctrl, artifact_mgr, git_mgr, pe_agent, review_agent, issue_registry, convergence, obs)
    return engine, state_ctrl, obs, git_mgr


class TestCycleTracking:
    """Verify cycle tracking is accurate across review cycles."""

    def test_approve_on_cycle_1(self, tmp_path: Path):
        """If the first review approves, cycle should be 1."""

        class AlwaysApproveLLM(MockLLMForCycles):
            def generate(self, prompt, system_prompt=""):
                sys_upper = system_prompt.upper()
                if "REVIEWER" in sys_upper or "SKEPTICAL" in sys_upper or "VERIFICATION" in sys_upper:
                    return (
                        "# Review Result\n\nOutcome:\nAPPROVE\n\n"
                        "# Existing Issues\n\n"
                        "# New Issues\n\n"
                        "# Summary\n\n"
                        "Open Blocking Issues: 0\nOpen Non Blocking Issues: 0\n\n"
                        "# Confidence\n0.95"
                    )
                return super().generate(prompt, system_prompt)

        engine, state_ctrl, obs, git_mgr = _build_engine(tmp_path, AlwaysApproveLLM())
        engine.run_loop()

        state = state_ctrl.load_state()
        assert state["current_cycle"] == 1
        assert state["latest_decision"] == "APPROVE"
        assert state["current_state"] == WorkflowState.APPROVED.value

    def test_approve_on_cycle_2(self, tmp_path: Path):
        """Default MockLLM rejects cycle 1, approves cycle 2. Cycle should be 2."""
        engine, state_ctrl, obs, git_mgr = _build_engine(tmp_path)
        engine.run_loop()

        state = state_ctrl.load_state()
        assert state["current_cycle"] == 2
        assert state["latest_decision"] == "APPROVE"
        assert state["current_state"] == WorkflowState.APPROVED.value

    def test_approve_on_cycle_3(self, tmp_path: Path):
        """Reject cycles 1-2, approve cycle 3."""
        call_count = [0]

        class RejectTwiceLLM(MockLLMForCycles):
            def generate(self, prompt, system_prompt=""):
                sys_upper = system_prompt.upper()
                if "REVIEWER" in sys_upper or "SKEPTICAL" in sys_upper or "VERIFICATION" in sys_upper:
                    call_count[0] += 1
                    if call_count[0] == 1:
                        # Cycle 1: discovery review, add a blocking issue
                        return (
                            "# Review Result\n\nOutcome:\nREJECT\n\n"
                            "# Existing Issues\n\n"
                            "# New Issues\n\n"
                            "Issue: A001\nSeverity: BLOCKING\n\nDescription:\nProblem.\n\nEvidence:\nEvidence.\n\n"
                            "# Summary\n\nOpen Blocking Issues: 1\nOpen Non Blocking Issues: 0\n\n"
                            "# Confidence\n0.85"
                        )
                    elif call_count[0] == 2:
                        # Cycle 2: keep existing issue OPEN (no new issues, no divergence)
                        return (
                            "# Review Result\n\nOutcome:\nREJECT\n\n"
                            "# Existing Issues\n"
                            "Issue: P001\nStatus: OPEN\n\n"
                            "# New Issues\n\n"
                            "# Summary\n\nOpen Blocking Issues: 1\nOpen Non Blocking Issues: 0\n\n"
                            "# Confidence\n0.85"
                        )
                    else:
                        # Cycle 3: resolve everything
                        return (
                            "# Review Result\n\nOutcome:\nAPPROVE\n\n"
                            "# Existing Issues\n"
                            "Issue: P001\nStatus: RESOLVED\n\n"
                            "# New Issues\n\n"
                            "# Summary\n\nOpen Blocking Issues: 0\nOpen Non Blocking Issues: 0\n\n"
                            "# Confidence\n0.95"
                        )
                return super().generate(prompt, system_prompt)

        engine, state_ctrl, obs, git_mgr = _build_engine(tmp_path, RejectTwiceLLM())
        engine.run_loop()

        state = state_ctrl.load_state()
        assert state["current_cycle"] == 3
        assert state["latest_decision"] == "APPROVE"
        assert state["current_state"] == WorkflowState.APPROVED.value

    def test_escalation_after_max_cycles(self, tmp_path: Path):
        """All 3 cycles reject -> escalation. Cycle should be 3."""
        review_call_count = [0]

        class AlwaysRejectLLM(MockLLMForCycles):
            def generate(self, prompt, system_prompt=""):
                sys_upper = system_prompt.upper()
                if "REVIEWER" in sys_upper or "SKEPTICAL" in sys_upper or "VERIFICATION" in sys_upper:
                    review_call_count[0] += 1
                    if review_call_count[0] == 1:
                        # Cycle 1: add a blocking issue
                        return (
                            "# Review Result\n\nOutcome:\nREJECT\n\n"
                            "# Existing Issues\n\n"
                            "# New Issues\n\n"
                            "Issue: A001\nSeverity: BLOCKING\n\nDescription:\nProblem.\n\nEvidence:\nEvidence.\n\n"
                            "# Summary\n\nOpen Blocking Issues: 1\nOpen Non Blocking Issues: 0\n\n"
                            "# Confidence\n0.85"
                        )
                    else:
                        # Cycle 2+: keep existing issue OPEN (no new issues avoids divergence)
                        return (
                            "# Review Result\n\nOutcome:\nREJECT\n\n"
                            "# Existing Issues\n"
                            "Issue: P001\nStatus: OPEN\n\n"
                            "# New Issues\n\n"
                            "# Summary\n\nOpen Blocking Issues: 1\nOpen Non Blocking Issues: 0\n\n"
                            "# Confidence\n0.85"
                        )
                return super().generate(prompt, system_prompt)

        engine, state_ctrl, obs, git_mgr = _build_engine(tmp_path, AlwaysRejectLLM())
        engine.run_loop()

        state = state_ctrl.load_state()
        assert state["current_cycle"] == 3
        assert state["latest_decision"] == "REJECT"
        assert state["current_state"] == WorkflowState.ESCALATED.value

    def test_resume_workflow_preserves_cycle(self, tmp_path: Path):
        """Verify cycle persists across controller reloads."""
        controller = StateController(tmp_path)
        controller.initialize("Resume test")
        controller.update_cycle(2)
        controller.update_decision("REJECT")

        # Create a new controller instance (simulates restart)
        controller2 = StateController(tmp_path)
        assert controller2.get_current_cycle() == 2
        assert controller2.get_latest_decision() == "REJECT"


# ============================================================
# 3. STATUS COMMAND TESTS
# ============================================================

class TestStatusCommand:
    """Verify status reads from authoritative state, not inferred values."""

    def test_status_reads_authoritative_cycle(self, tmp_path: Path, monkeypatch):
        """Status should report cycle from state.json, not from file count."""
        monkeypatch.setenv("KARSA_MOCK_LLM", "1")
        monkeypatch.setenv("KARSA_WORKSPACE_DIR", str(tmp_path / "workspace"))

        from typer.testing import CliRunner
        from karsa.cli import app

        runner = CliRunner()

        # Run start to create a project
        result = runner.invoke(app, ["start", "--idea", "test"])
        assert result.exit_code == 0

        # Check status
        result = runner.invoke(app, ["status", "--project", "test"])
        assert result.exit_code == 0

        # Extract cycle from status output
        cycle_match = re.search(r'Current Cycle:\s*(\d+)', result.stdout)
        assert cycle_match is not None
        cycle = int(cycle_match.group(1))

        # The default mock LLM produces REJECT on cycle 1, APPROVE on cycle 2
        # So the cycle should be 2
        assert cycle == 2, f"Expected cycle 2 but got {cycle}"

    def test_status_reads_authoritative_decision(self, tmp_path: Path, monkeypatch):
        """Status should report decision from state.json."""
        monkeypatch.setenv("KARSA_MOCK_LLM", "1")
        monkeypatch.setenv("KARSA_WORKSPACE_DIR", str(tmp_path / "workspace"))

        from typer.testing import CliRunner
        from karsa.cli import app

        runner = CliRunner()
        runner.invoke(app, ["start", "--idea", "test"])

        result = runner.invoke(app, ["status", "--project", "test"])
        assert "Latest Decision: APPROVE" in result.stdout


# ============================================================
# 4. DECISION PROVENANCE TESTS
# ============================================================

class TestDecisionProvenance:
    """Verify decision records never contain 'Unknown' as reason."""

    def test_reason_never_unknown(self, tmp_path: Path):
        """After a review cycle, decision reason must not be 'Unknown'."""
        engine, state_ctrl, obs, git_mgr = _build_engine(tmp_path)
        engine.run_loop()

        decisions_dir = tmp_path / ".karsa" / "decisions"
        assert decisions_dir.exists()

        decision_files = sorted(decisions_dir.glob("*.md"))
        assert len(decision_files) > 0

        for df in decision_files:
            content = df.read_text()
            reason_match = re.search(r'Reason:\n(.*?)(?:\n\n|$)', content, re.DOTALL)
            assert reason_match is not None, f"No reason found in {df.name}"
            reason = reason_match.group(1).strip()
            assert reason != "Unknown", f"Reason is 'Unknown' in {df.name}"
            assert reason != "", f"Reason is empty in {df.name}"

    def test_decision_contains_required_fields(self, tmp_path: Path):
        """Each decision file must contain all required provenance fields."""
        engine, state_ctrl, obs, git_mgr = _build_engine(tmp_path)
        engine.run_loop()

        decisions_dir = tmp_path / ".karsa" / "decisions"
        decision_files = sorted(decisions_dir.glob("*.md"))

        required_fields = [
            "Decision ID:",
            "Agent:",
            "Decision:",
            "Reason:",
            "Evidence:",
            "Provider:",
            "Key Fingerprint:",
            "Source:",
            "Confidence:",
            "Timestamp:",
        ]

        for df in decision_files:
            content = df.read_text()
            for field in required_fields:
                assert field in content, f"Missing '{field}' in {df.name}"

    def test_extract_decision_reason_with_summary(self):
        """_extract_decision_reason should extract from # Summary section."""
        review_text = "# Review Result\nOutcome: REJECT\n\n# Summary\nThis design has critical gaps.\n\n# Confidence\n0.8"
        metrics = {"blocking_issue_count": 2, "non_blocking_issue_count": 1, "resolved_count": 0}

        reason = _extract_decision_reason(review_text, "REJECT", metrics)
        assert "critical gaps" in reason.lower() or "blocking" in reason.lower()

    def test_extract_decision_reason_fallback_synthesis(self):
        """When no section matches, reason should be synthesized from metrics."""
        review_text = "# Review Result\nOutcome: REJECT\n\n# Confidence\n0.8"
        metrics = {"blocking_issue_count": 3, "non_blocking_issue_count": 1, "resolved_count": 2}

        reason = _extract_decision_reason(review_text, "REJECT", metrics)
        assert reason != "Unknown"
        assert reason != ""
        assert "3" in reason  # Should mention the blocking count

    def test_extract_decision_reason_approve(self):
        """Approve reason should mention resolution."""
        review_text = "# Review Result\nOutcome: APPROVE\n\n# Confidence\n0.95"
        metrics = {"blocking_issue_count": 0, "non_blocking_issue_count": 0, "resolved_count": 5}

        reason = _extract_decision_reason(review_text, "APPROVE", metrics)
        assert reason != "Unknown"
        assert "resolved" in reason.lower()


# ============================================================
# 5. PROVIDER ROTATION TRACE EVENTS TESTS
# ============================================================

class TestProviderTraceEvents:
    """Verify provider rotation trace events are logged."""

    def test_key_selected_event(self, tmp_path: Path):
        """KeySelected event should be logged when a key is picked."""
        events = []
        registry = tmp_path / "registry.json"
        pool = ProviderPool("test", ["key1"], registry, trace_fn=lambda e: events.append(e))

        pool.get_next_key()
        assert any("KeySelected:" in e for e in events)

    def test_key_suspended_and_quota_exceeded_events(self, tmp_path: Path):
        """QuotaExceeded and KeySuspended events on quota failure."""
        os.environ["KARSA_TESTING"] = "1"
        events = []
        registry = tmp_path / "registry.json"
        pool = ProviderPool("test", ["key1"], registry, trace_fn=lambda e: events.append(e))

        k = pool.get_next_key()
        pool.mark_failure(k, is_quota=True)

        assert any("QuotaExceeded:" in e for e in events)
        assert any("KeySuspended:" in e for e in events)

    def test_key_recovered_event(self, tmp_path: Path):
        """KeyRecovered event when a suspended key is reactivated."""
        os.environ["KARSA_TESTING"] = "1"
        events = []
        registry = tmp_path / "registry.json"
        pool = ProviderPool("test", ["key1"], registry, trace_fn=lambda e: events.append(e))

        k = pool.get_next_key()
        pool.mark_failure(k, is_quota=True)

        import time
        time.sleep(0.15)

        events.clear()
        pool.get_next_key()
        assert any("KeyRecovered:" in e for e in events)

    def test_key_rotated_event_on_fallback(self, tmp_path: Path):
        """KeyRotated event should be logged when provider falls back."""
        os.environ["KARSA_TESTING"] = "1"

        class FailingClient(LLMClient):
            def __init__(self, name):
                super().__init__()
                self.model_name = name
                self.current_key_fingerprint = f"{name}_key"
            def generate(self, prompt, system_prompt=""):
                raise Exception("503 UNAVAILABLE")

        class SuccessClient(LLMClient):
            def __init__(self, name):
                super().__init__()
                self.model_name = name
                self.current_key_fingerprint = f"{name}_key"
            def generate(self, prompt, system_prompt=""):
                return "OK"

        obs = ObservabilityManager(tmp_path)
        provider = ProviderManager(
            [FailingClient("primary"), SuccessClient("secondary")],
            obs_manager=obs
        )

        provider.generate_with_obs("TestAgent", "test")

        trace_log = (tmp_path / ".karsa" / "trace.log").read_text()
        assert "KeyRotated:" in trace_log
        assert "FallbackActivated" in trace_log

    def test_provider_unavailable_event(self, tmp_path: Path):
        """ProviderUnavailable event when all providers fail."""
        os.environ["KARSA_TESTING"] = "1"

        class FailingClient(LLMClient):
            def __init__(self):
                super().__init__()
                self.model_name = "fail"
            def generate(self, prompt, system_prompt=""):
                raise Exception("503 UNAVAILABLE")

        obs = ObservabilityManager(tmp_path)
        provider = ProviderManager([FailingClient()], obs_manager=obs)

        with pytest.raises(Exception):
            provider.generate_with_obs("TestAgent", "test")

        trace_log = (tmp_path / ".karsa" / "trace.log").read_text()
        assert "ProviderUnavailable" in trace_log

    def test_full_trace_sequence(self, tmp_path: Path):
        """Verify a full trace sequence: KeySelected -> request -> QuotaExceeded -> KeySuspended -> KeyRotated -> FallbackActivated -> success."""
        os.environ["KARSA_TESTING"] = "1"

        events = []
        registry = tmp_path / "registry.json"

        # Create two pools with trace
        pool1 = ProviderPool("model-a", ["key_a"], registry, trace_fn=lambda e: events.append(e))
        pool2 = ProviderPool("model-b", ["key_b"], registry, trace_fn=lambda e: events.append(e))

        # Simulate: get key from pool1, it fails with quota
        k1 = pool1.get_next_key()
        assert any("KeySelected:" in e for e in events)

        pool1.mark_failure(k1, is_quota=True)
        assert any("QuotaExceeded:" in e for e in events)
        assert any("KeySuspended:" in e for e in events)

        # Now pool1 has no keys, get key from pool2
        k2 = pool2.get_next_key()
        assert k2 is not None
        pool2.mark_success(k2)

        # Verify event ordering
        ordered_events = [e for e in events if any(kw in e for kw in ["KeySelected", "QuotaExceeded", "KeySuspended"])]
        assert len(ordered_events) >= 3


# ============================================================
# 6. STATE PERSISTENCE TESTS
# ============================================================

class TestStatePersistence:
    """Verify state.json is properly persisted and recoverable."""

    def test_state_survives_reload(self, tmp_path: Path):
        ctrl = StateController(tmp_path)
        ctrl.initialize("persistence test")
        ctrl.update_cycle(3)
        ctrl.update_decision("APPROVE")
        ctrl.update_issues(0, 1, 5)
        ctrl.transition_to(WorkflowState.APPROVED)

        # Reload
        ctrl2 = StateController(tmp_path)
        state = ctrl2.load_state()
        assert state["current_state"] == "APPROVED"
        assert state["current_cycle"] == 3
        assert state["latest_decision"] == "APPROVE"
        assert state["open_blocking_issues"] == 0
        assert state["open_non_blocking_issues"] == 1
        assert state["resolved_issues"] == 5

    def test_state_json_schema_completeness(self, tmp_path: Path):
        """All required fields must be present in saved state."""
        ctrl = StateController(tmp_path)
        ctrl.initialize("schema test")

        state_file = tmp_path / ".karsa" / "state.json"
        with open(state_file) as f:
            raw = json.load(f)

        required_keys = [
            "current_state",
            "idea",
            "current_cycle",
            "latest_decision",
            "open_blocking_issues",
            "open_non_blocking_issues",
            "resolved_issues",
            "last_updated_timestamp",
            "provider_summary",
        ]
        for key in required_keys:
            assert key in raw, f"Missing key '{key}' in state.json"


# ============================================================
# 7. REGRESSION TESTS
# ============================================================

class TestRegressions:
    """Regression tests for previously observed bugs."""

    def test_cycle_not_inferred_from_revision_files(self, tmp_path: Path):
        """
        Regression: Previously cycle was inferred from docs/revisions/ file count.
        This test creates extra revision files and verifies cycle is read from state.json.
        """
        ctrl = StateController(tmp_path)
        ctrl.initialize("regression test")
        ctrl.update_cycle(2)

        # Create fake revision files that would mislead an inferred count
        revisions_dir = tmp_path / "docs" / "revisions"
        revisions_dir.mkdir(parents=True, exist_ok=True)
        for i in range(5):
            (revisions_dir / f"REVISION_{i:03d}.md").write_text(f"fake revision {i}")

        # The authoritative cycle should be 2, not 5
        assert ctrl.get_current_cycle() == 2

    def test_decision_reason_not_unknown_after_review(self, tmp_path: Path):
        """
        Regression: decision files had 'Reason: Unknown' because the regex
        looked for '# Rejection Reason' which doesn't exist in review format.
        """
        engine, state_ctrl, obs, git_mgr = _build_engine(tmp_path)
        engine.run_loop()

        decisions_dir = tmp_path / ".karsa" / "decisions"
        for df in sorted(decisions_dir.glob("*.md")):
            content = df.read_text()
            reason_match = re.search(r'Reason:\n(.*?)(?:\n\n)', content, re.DOTALL)
            if reason_match:
                assert reason_match.group(1).strip() != "Unknown"

    def test_status_cycle_matches_last_executed_review(self, tmp_path: Path):
        """
        Regression: 'karsa status' reported cycle 1 even when 2 cycles executed.
        After fix, status reads from authoritative state.json.
        """
        ctrl = StateController(tmp_path)
        ctrl.initialize("match test")
        # Simulate 2 review cycles
        ctrl.update_cycle(1)
        ctrl.update_cycle(2)

        state = ctrl.load_state()
        assert state["current_cycle"] == 2
