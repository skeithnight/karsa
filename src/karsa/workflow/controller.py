import json
from pathlib import Path
from typing import Optional
from karsa.models.state import WorkflowState

class StateController:
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.karsa_dir = self.workspace_dir / ".karsa"
        self.state_file = self.karsa_dir / "state.json"

    def initialize(self, idea: str):
        self.karsa_dir.mkdir(parents=True, exist_ok=True)
        initial_state = {
            "current_state": WorkflowState.IDEA.value,
            "idea": idea
        }
        self.save_state(initial_state)
    
    def save_state(self, state_dict: dict):
        with open(self.state_file, "w") as f:
            json.dump(state_dict, f, indent=4)

    def load_state(self) -> dict:
        if not self.state_file.exists():
            return {}
        with open(self.state_file, "r") as f:
            return json.load(f)

    def transition_to(self, new_state: WorkflowState):
        state = self.load_state()
        state["current_state"] = new_state.value
        self.save_state(state)
        
    def get_current_state(self) -> Optional[WorkflowState]:
        state = self.load_state()
        state_value = state.get("current_state")
        return WorkflowState(state_value) if state_value else None
