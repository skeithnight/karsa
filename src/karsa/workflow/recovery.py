from typing import Optional
from karsa.domain.models import WorkflowSnapshot, WorkflowState
from karsa.domain.events import WorkflowCreatedEvent, StateTransitionedEvent
from karsa.domain.persistence import SnapshotRepository, EventJournalRepository

class RecoveryEngine:
    def __init__(self, snapshot_repo: SnapshotRepository, event_repo: EventJournalRepository):
        self.snapshot_repo = snapshot_repo
        self.event_repo = event_repo
        
    def rehydrate(self, workflow_id: str) -> Optional[WorkflowSnapshot]:
        # 1. Load base state
        snapshot = self.snapshot_repo.load(workflow_id)
        
        # 2. Load events
        events = self.event_repo.load(workflow_id)
        
        # 3. Apply un-snapshotted events
        if not snapshot:
            if not events:
                return None
            
            # Need to initialize from first event if it's a create
            first_event = events[0]
            if isinstance(first_event, WorkflowCreatedEvent):
                snapshot = WorkflowSnapshot(
                    workflow_id=workflow_id,
                    state=WorkflowState.IDEA,
                    last_sequence_number=first_event.sequence_number
                )
            else:
                raise ValueError("Cannot rehydrate workflow without Snapshot or WorkflowCreatedEvent")
                
        for event in events:
            # Skip events already in snapshot
            seq = getattr(event, 'sequence_number', 0)
            if seq <= snapshot.last_sequence_number:
                continue
                
            if isinstance(event, StateTransitionedEvent):
                snapshot.state = event.new_state
                snapshot.last_sequence_number = event.sequence_number
                
        return snapshot
