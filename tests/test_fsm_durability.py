import pytest
import shutil
from pathlib import Path
from karsa.domain.models import WorkflowState, WorkflowSnapshot
from karsa.domain.events import WorkflowCreatedEvent, StateTransitionedEvent
from karsa.domain.persistence import SnapshotRepository, EventJournalRepository
from karsa.workflow.fsm import StateTransitionEngine, InvalidTransitionError
from karsa.workflow.recovery import RecoveryEngine
from karsa.workflow.lock import WorkflowLockManager, WorkflowLockedError

TEST_WORKSPACE = Path("test_sprint2_workspace")

@pytest.fixture(autouse=True)
def cleanup():
    if TEST_WORKSPACE.exists():
        shutil.rmtree(TEST_WORKSPACE)
    TEST_WORKSPACE.mkdir(parents=True)
    yield
    if TEST_WORKSPACE.exists():
        shutil.rmtree(TEST_WORKSPACE)

def test_fsm_valid_transitions():
    engine = StateTransitionEngine()
    event = engine.transition("w1", WorkflowState.IDEA, WorkflowState.DRAFT, reason="started")
    assert event.new_state == WorkflowState.DRAFT
    
def test_fsm_invalid_transitions():
    engine = StateTransitionEngine()
    with pytest.raises(InvalidTransitionError):
        engine.transition("w1", WorkflowState.IDEA, WorkflowState.APPROVED)

def test_workflow_lock():
    lock_mgr = WorkflowLockManager(TEST_WORKSPACE, ttl_seconds=2)
    lock_mgr.acquire("w1", "proc1")
    
    with pytest.raises(WorkflowLockedError):
        lock_mgr.acquire("w1", "proc2")
        
    lock_mgr.release("w1", "proc1")
    lock_mgr.acquire("w1", "proc2")

def test_hybrid_persistence_and_recovery():
    snap_repo = SnapshotRepository(TEST_WORKSPACE)
    event_repo = EventJournalRepository(TEST_WORKSPACE)
    recovery = RecoveryEngine(snap_repo, event_repo)
    
    workflow_id = "w_crash"
    
    snap = WorkflowSnapshot(
        workflow_id=workflow_id,
        state=WorkflowState.IDEA,
        schema_version=1,
        last_sequence_number=1
    )
    snap_repo.save(snap)
    
    e1 = StateTransitionedEvent(
        workflow_id=workflow_id,
        previous_state=WorkflowState.IDEA,
        new_state=WorkflowState.DRAFT,
        sequence_number=2
    )
    e2 = StateTransitionedEvent(
        workflow_id=workflow_id,
        previous_state=WorkflowState.DRAFT,
        new_state=WorkflowState.REVIEW,
        sequence_number=3
    )
    event_repo.append(workflow_id, e1)
    event_repo.append(workflow_id, e2)
    
    recovered_snap = recovery.rehydrate(workflow_id)
    assert recovered_snap.workflow_id == workflow_id
    assert recovered_snap.state == WorkflowState.REVIEW
    assert recovered_snap.last_sequence_number == 3

def test_recovery_from_events_only():
    snap_repo = SnapshotRepository(TEST_WORKSPACE)
    event_repo = EventJournalRepository(TEST_WORKSPACE)
    recovery = RecoveryEngine(snap_repo, event_repo)
    
    workflow_id = "w_no_snap"
    
    e0 = WorkflowCreatedEvent(workflow_id=workflow_id, sequence_number=1)
    e1 = StateTransitionedEvent(
        workflow_id=workflow_id,
        previous_state=WorkflowState.IDEA,
        new_state=WorkflowState.FAILED,
        sequence_number=2
    )
    event_repo.append(workflow_id, e0)
    event_repo.append(workflow_id, e1)
    
    recovered_snap = recovery.rehydrate(workflow_id)
    assert recovered_snap.state == WorkflowState.FAILED
    assert recovered_snap.last_sequence_number == 2

def test_recovery_is_deterministic():
    snap_repo = SnapshotRepository(TEST_WORKSPACE)
    event_repo = EventJournalRepository(TEST_WORKSPACE)
    recovery = RecoveryEngine(snap_repo, event_repo)
    
    workflow_id = "w_det_test"
    
    # 1. Populate metrics in data to mimic the real execution context
    data_context = {
        "metrics": {
            "total_cost": 0.045,
            "total_tokens": 1250,
            "execution_count": 5
        },
        "review": {
            "review_cycle_id": "rc_99",
            "review_cycle_metrics": {
                "total_cost": 0.01,
                "total_tokens": 300,
                "execution_count": 2
            }
        }
    }
    
    # 2. Base Snapshot
    original_workflow = WorkflowSnapshot(
        workflow_id=workflow_id,
        state=WorkflowState.REVIEW,
        data=data_context,
        schema_version=1,
        last_sequence_number=10
    )
    snap_repo.save(original_workflow)
    
    # 3. Add an event moving it to REVISE, which means the crash happened BEFORE the snap compacted this transition
    e1 = StateTransitionedEvent(
        workflow_id=workflow_id,
        previous_state=WorkflowState.REVIEW,
        new_state=WorkflowState.REVISE,
        sequence_number=11
    )
    event_repo.append(workflow_id, e1)
    
    # Also update the theoretical "original" state to match what it *should* look like perfectly after the event
    expected_workflow = WorkflowSnapshot(
        workflow_id=workflow_id,
        state=WorkflowState.REVISE,
        data=data_context, # data remains the same since transition event only mutated state and seq
        schema_version=1,
        last_sequence_number=11
    )
    
    # 4. Recover
    recovered_workflow = recovery.rehydrate(workflow_id)
    
    # 5. Deep Equality Field-by-Field
    assert recovered_workflow.workflow_id == expected_workflow.workflow_id
    assert recovered_workflow.state == expected_workflow.state
    assert recovered_workflow.schema_version == expected_workflow.schema_version
    assert recovered_workflow.last_sequence_number == expected_workflow.last_sequence_number
    assert recovered_workflow.data == expected_workflow.data
    
    # Absolute Object Equality (Dataclass comparison)
    assert recovered_workflow == expected_workflow
