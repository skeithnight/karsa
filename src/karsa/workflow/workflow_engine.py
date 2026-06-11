from typing import Optional, Any, Callable
from karsa.domain.models import WorkflowSnapshot, WorkflowState, GovernanceDecision
from karsa.domain.events import DomainEvent, GovernanceDecisionEvent, WorkflowAbortedEvent, StateTransitionedEvent
from karsa.domain.persistence import SnapshotRepository, EventJournalRepository
from karsa.workflow.fsm import StateTransitionEngine
from karsa.governance.evaluator import GovernanceEvaluator
from karsa.workflow.snapshot_strategy import SnapshotStrategy, SnapshotStrategyConfig
import threading

class WorkflowEngine:
    def __init__(self, 
                 snapshot_repo: SnapshotRepository, 
                 event_repo: EventJournalRepository, 
                 fsm: StateTransitionEngine,
                 evaluator: GovernanceEvaluator,
                 is_replaying: bool = False):
        self.snapshot_repo = snapshot_repo
        self.event_repo = event_repo
        self.fsm = fsm
        self.evaluator = evaluator
        self.is_replaying = is_replaying
        self._lock = threading.Lock()
        
        self.snapshot: Optional[WorkflowSnapshot] = None
        self._current_sequence: int = 0
        self._events_since_snapshot: int = 0
        self.snapshot_strategy = SnapshotStrategy(SnapshotStrategyConfig(), self.event_repo)
        
    def load(self, workflow_id: str):
        self.snapshot = self.snapshot_repo.load(workflow_id)
        if self.snapshot:
            self._current_sequence = self.snapshot.last_sequence_number
            
    def _next_seq(self) -> int:
        self._current_sequence += 1
        return self._current_sequence

    def append_event(self, event: DomainEvent) -> DomainEvent:
        if self.is_replaying:
            return event
            
        with self._lock:
            seq = self._next_seq()
            event.sequence_number = seq
            if self.snapshot:
                self.event_repo.append(self.snapshot.workflow_id, event)
                self.snapshot.last_sequence_number = seq
                self._events_since_snapshot += 1
                
                if self.snapshot_strategy.should_snapshot(self.snapshot, self._events_since_snapshot):
                    self.snapshot_repo.save(self.snapshot)
                    self._events_since_snapshot = 0
            return event
            
    def transition_state(self, new_state: WorkflowState, reason: str = "") -> bool:
        if self.is_replaying or not self.snapshot:
            return False
            
        with self._lock:
            fsm_event = self.fsm.transition(self.snapshot.workflow_id, self.snapshot.state, new_state, reason=reason)
            seq = self._next_seq()
            fsm_event.sequence_number = seq
            self.event_repo.append(self.snapshot.workflow_id, fsm_event)
            
            self.snapshot.state = new_state
            self.snapshot.last_sequence_number = seq
            self._events_since_snapshot += 1
            
            if self.snapshot_strategy.should_snapshot(self.snapshot, self._events_since_snapshot):
                self.snapshot_repo.save(self.snapshot)
                self._events_since_snapshot = 0
                
            return True

    def check_governance(self, execution_id: str, review_cycle_id: str) -> bool:
        """Returns True if ALLOWED, False if DENIED and ABORTED"""
        if not self.snapshot or self.is_replaying:
            return True
            
        decision = self.evaluator.evaluate(self.snapshot, execution_id, review_cycle_id)
        if decision.decision_type == "DENY":
            decision_event = GovernanceDecisionEvent(decision=decision)
            self.append_event(decision_event)
            
            self.transition_state(WorkflowState.ABORTED, reason=decision.reason)
            
            abort_event = WorkflowAbortedEvent(workflow_id=self.snapshot.workflow_id, reason=decision.reason)
            self.append_event(abort_event)
            return False
        return True
