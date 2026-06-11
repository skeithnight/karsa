import json
from pathlib import Path
from typing import Optional, List
from karsa.models.state import WorkflowState
from karsa.observability.trace import get_iso_timestamp

class StateController:
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.karsa_dir = self.workspace_dir / ".karsa"
        self.state_file = self.karsa_dir / "state.json"

    def initialize(self, idea: str):
        self.karsa_dir.mkdir(parents=True, exist_ok=True)
        initial_state = {
            "current_state": WorkflowState.IDEA.value,
            "idea": idea,
            "current_cycle": 0,
            "latest_decision": "NONE",
            "open_blocking_issues": 0,
            "open_non_blocking_issues": 0,
            "resolved_issues": 0,
            "last_updated_timestamp": get_iso_timestamp(),
            "provider_summary": {}
        }
        self.save_state(initial_state)
        metadata = {
            "project_name": idea,
            "version": "0.1.0"
        }
        with open(self.karsa_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=4)
    
    def save_state(self, state_dict: dict):
        state_dict["last_updated_timestamp"] = get_iso_timestamp()
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

    def update_cycle(self, cycle: int):
        """Update the current review cycle number in authoritative state."""
        state = self.load_state()
        state["current_cycle"] = cycle
        self.save_state(state)

    def update_decision(self, decision: str):
        """Update the latest decision in authoritative state."""
        state = self.load_state()
        state["latest_decision"] = decision
        self.save_state(state)

    def update_issues(self, blocking: int, non_blocking: int, resolved: int):
        """Update issue counts in authoritative state."""
        state = self.load_state()
        state["open_blocking_issues"] = blocking
        state["open_non_blocking_issues"] = non_blocking
        state["resolved_issues"] = resolved
        self.save_state(state)

    def update_provider_summary(self, summary: dict):
        """Update provider summary in authoritative state."""
        state = self.load_state()
        state["provider_summary"] = summary
        self.save_state(state)

    def get_current_cycle(self) -> int:
        """Get the current cycle from authoritative state."""
        state = self.load_state()
        return state.get("current_cycle", 0)

    def get_latest_decision(self) -> str:
        """Get the latest decision from authoritative state."""
        state = self.load_state()
        return state.get("latest_decision", "NONE")
