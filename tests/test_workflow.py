from karsa.workflow.controller import StateController
from karsa.models.state import WorkflowState
from pathlib import Path

def test_state_controller_initialize(tmp_path: Path):
    controller = StateController(tmp_path)
    controller.initialize("Test idea")
    
    state = controller.load_state()
    assert state["current_state"] == WorkflowState.IDEA.value
    assert state["idea"] == "Test idea"
    assert controller.get_current_state() == WorkflowState.IDEA

def test_state_controller_transition(tmp_path: Path):
    controller = StateController(tmp_path)
    controller.initialize("Test idea")
    controller.transition_to(WorkflowState.RESEARCH)
    
    state = controller.load_state()
    assert state["current_state"] == WorkflowState.RESEARCH.value
    assert controller.get_current_state() == WorkflowState.RESEARCH
