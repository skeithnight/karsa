from karsa.domain.models import WorkflowState
from karsa.domain.events import StateTransitionedEvent

class InvalidTransitionError(Exception):
    pass

class StateTransitionEngine:
    VALID_TRANSITIONS = {
        WorkflowState.IDEA: [WorkflowState.DRAFT, WorkflowState.FAILED, WorkflowState.ABORTED, WorkflowState.SUSPENDED],
        WorkflowState.DRAFT: [WorkflowState.REVIEW, WorkflowState.FAILED, WorkflowState.ABORTED, WorkflowState.SUSPENDED],
        WorkflowState.REVIEW: [WorkflowState.REVISE, WorkflowState.APPROVED, WorkflowState.FAILED, WorkflowState.ABORTED, WorkflowState.SUSPENDED, WorkflowState.ESCALATED],
        WorkflowState.REVISE: [WorkflowState.REVIEW, WorkflowState.FAILED, WorkflowState.ABORTED, WorkflowState.SUSPENDED],
        WorkflowState.APPROVED: [],
        WorkflowState.FAILED: [],
        WorkflowState.ABORTED: [],
        WorkflowState.ESCALATED: [],
        WorkflowState.SUSPENDED: [WorkflowState.DRAFT, WorkflowState.REVIEW, WorkflowState.REVISE, WorkflowState.ABORTED]
    }

    def __init__(self):
        pass
        
    def transition(self, workflow_id: str, current: WorkflowState, target: WorkflowState, reason: str = "", sequence_number: int = 0) -> StateTransitionedEvent:
        if target not in self.VALID_TRANSITIONS.get(current, []):
            raise InvalidTransitionError(f"Cannot transition from {current.name} to {target.name}")
            
        return StateTransitionedEvent(
            workflow_id=workflow_id,
            previous_state=current,
            new_state=target,
            reason=reason,
            sequence_number=sequence_number
        )
