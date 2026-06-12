from karsa.domain.models import WorkflowState
from karsa.workflow.workflow_engine import WorkflowEngine
from karsa.workflow.orchestrator import AgentOrchestrator
from karsa.artifacts.projection import ProjectionManager
from karsa.workflow.recovery import RecoveryEngine
import time

class WorkflowRunner:
    def __init__(self, engine: WorkflowEngine, orchestrator: AgentOrchestrator, projection: ProjectionManager, recovery: RecoveryEngine):
        self.engine = engine
        self.orchestrator = orchestrator
        self.projection = projection
        self.recovery = recovery

    def start_workflow(self, workflow_id: str):
        self.engine.load(workflow_id)
        
        # Initial projection sync
        self.projection.reconcile_all(self.engine.snapshot)
        
        cycle_id = 1
        
        while self.engine.snapshot.state not in [WorkflowState.APPROVED, WorkflowState.FAILED, WorkflowState.ABORTED, WorkflowState.ESCALATED, WorkflowState.SUSPENDED]:
            
            # Governance Check before execution
            if not self.engine.check_governance("exec_" + str(time.time()), str(cycle_id)):
                break # Engine will transition to ABORTED internally
                
            outcome = self.orchestrator.execute_cycle(cycle_id)
            
            if outcome == "APPROVED":
                if self.engine.snapshot.state == WorkflowState.REVISE:
                    self.engine.transition_state(WorkflowState.REVIEW)
                self.engine.transition_state(WorkflowState.APPROVED)
            elif outcome == "REVISE":
                if self.engine.snapshot.state == WorkflowState.REVISE:
                    self.engine.transition_state(WorkflowState.REVIEW)
                self.engine.transition_state(WorkflowState.REVISE)
                cycle_id += 1
            elif outcome == "ESCALATED":
                if self.engine.snapshot.state == WorkflowState.REVISE:
                    self.engine.transition_state(WorkflowState.REVIEW)
                self.engine.transition_state(WorkflowState.ESCALATED)
            elif outcome == "SUSPENDED":
                self.engine.transition_state(WorkflowState.SUSPENDED)
                break
            elif outcome == "FAILED":
                self.engine.transition_state(WorkflowState.FAILED)
                break
                
            # After state transition, sync the projection synchronously
            self.projection.reconcile_all(self.engine.snapshot)
            
    def suspend(self):
        if self.engine.snapshot:
            self.engine.transition_state(WorkflowState.SUSPENDED)
            self.projection.reconcile_all(self.engine.snapshot)
            
    def resume(self, workflow_id: str):
        self.engine.load(workflow_id)
        if self.engine.snapshot and self.engine.snapshot.state == WorkflowState.SUSPENDED:
            self.engine.transition_state(WorkflowState.REVISE)
            self.projection.reconcile_all(self.engine.snapshot)
            self.start_workflow(workflow_id)
