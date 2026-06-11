import pytest
import shutil
import json
from pathlib import Path
from karsa.domain.models import WorkflowState, WorkflowSnapshot
from karsa.domain.persistence import SnapshotRepository, EventJournalRepository
from karsa.workflow.fsm import StateTransitionEngine
from karsa.workflow.recovery import RecoveryEngine
from karsa.workflow.workflow_engine import WorkflowEngine
from karsa.governance.config import ConfigurationLoader
from karsa.governance.evaluator import GovernanceEvaluator

EVIDENCE_WORKSPACE = Path("evidence_workspace")
if EVIDENCE_WORKSPACE.exists():
    shutil.rmtree(EVIDENCE_WORKSPACE)
EVIDENCE_WORKSPACE.mkdir()

TOML_PATH = EVIDENCE_WORKSPACE / "karsa.toml"
with open(TOML_PATH, "w") as f:
    f.write("max_review_cycles = 3\n")

loader = ConfigurationLoader(TOML_PATH)
policy = loader.create_snapshot()

snap_repo = SnapshotRepository(EVIDENCE_WORKSPACE)
event_repo = EventJournalRepository(EVIDENCE_WORKSPACE)
fsm = StateTransitionEngine()
evaluator = GovernanceEvaluator()
engine = WorkflowEngine(snap_repo, event_repo, fsm, evaluator)

wid = "w_audit"
snap = WorkflowSnapshot(wid, WorkflowState.REVIEW, policy=policy, data={"metrics": {"execution_count": 3}}, last_sequence_number=10)
snap_repo.save(snap)
engine.load(wid)
engine.process("e1", "r1", lambda: None)

# Print raw jsonl
with open(EVIDENCE_WORKSPACE / ".karsa" / "workflows" / wid / "events.jsonl", "r") as f:
    print(f.read())
