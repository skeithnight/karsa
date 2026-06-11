from typing import Optional, Any, Callable
from karsa.domain.models import WorkflowSnapshot, WorkflowState, GovernanceDecision
from karsa.domain.events import GovernanceDecisionEvent, WorkflowAbortedEvent, StateTransitionedEvent
from karsa.domain.persistence import SnapshotRepository, EventJournalRepository
from karsa.workflow.fsm import StateTransitionEngine
from karsa.governance.evaluator import GovernanceEvaluator

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
        
        self._snapshot: Optional[WorkflowSnapshot] = None
        self._current_sequence: int = 0
        
    def load(self, workflow_id: str):
        self._snapshot = self.snapshot_repo.load(workflow_id)
        if self._snapshot:
            self._current_sequence = self._snapshot.last_sequence_number
            
    def _next_seq(self) -> int:
        self._current_sequence += 1
        return self._current_sequence
        
    def _evaluate_governance(self, execution_id: str, review_cycle_id: str) -> bool:
        if not self._snapshot:
            return True
            
        decision = self.evaluator.evaluate(self._snapshot, execution_id, review_cycle_id)
        
        if decision.decision_type == "DENY":
            # 1. create GovernanceDecisionEvent
            seq = self._next_seq()
            decision_event = GovernanceDecisionEvent(decision=decision, sequence_number=seq)
            
            # 2. append to event stream
            if not self.is_replaying:
                self.event_repo.append(self._snapshot.workflow_id, decision_event)
                
                # 3. transition workflow to ABORTED
                fsm_event = self.fsm.transition(self._snapshot.workflow_id, self._snapshot.state, WorkflowState.ABORTED, reason=decision.reason)
                seq_fsm = self._next_seq()
                fsm_event.sequence_number = seq_fsm
                self.event_repo.append(self._snapshot.workflow_id, fsm_event)
                
                self._snapshot.state = WorkflowState.ABORTED
                self._snapshot.last_sequence_number = seq_fsm
                self.snapshot_repo.save(self._snapshot)
                
                # 4. emit WorkflowAbortedEvent
                seq_abort = self._next_seq()
                abort_event = WorkflowAbortedEvent(workflow_id=self._snapshot.workflow_id, reason=decision.reason, sequence_number=seq_abort)
                self.event_repo.append(self._snapshot.workflow_id, abort_event)
                
            return False
            
        return True
        
    def process(self, execution_id: str, review_cycle_id: str, step_logic: Callable[[], None]):
        if not self._snapshot or self._snapshot.state == WorkflowState.ABORTED:
            return
            
        # Before execution: evaluate governance
        if not self._evaluate_governance(execution_id, review_cycle_id):
            return # Aborted
            
        # Execute logic
        if not self.is_replaying:
            step_logic()
            
        # After execution: evaluate governance again
        if not self._evaluate_governance(execution_id, review_cycle_id):
            return # Aborted
