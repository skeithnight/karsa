import json
import os
from pathlib import Path
from typing import List, Optional, Any, Dict
from karsa.domain.models import WorkflowSnapshot, WorkflowState
from karsa.domain.events import DomainEvent, WorkflowCreatedEvent, StateTransitionedEvent, WorkflowFailedEvent

def serialize_event(event: DomainEvent) -> Dict[str, Any]:
    # Handle enums
    payload = {}
    for k, v in event.__dict__.items():
        if isinstance(v, WorkflowState):
            payload[k] = v.value
        else:
            payload[k] = v
    return {
        "event_type": type(event).__name__,
        "payload": payload
    }

def deserialize_event(data: Dict[str, Any]) -> DomainEvent:
    event_type = data.get("event_type")
    payload = data.get("payload", {})
    
    # Rehydrate Enum
    if "previous_state" in payload:
        payload["previous_state"] = WorkflowState(payload["previous_state"])
    if "new_state" in payload:
        payload["new_state"] = WorkflowState(payload["new_state"])
        
    if event_type == "WorkflowCreatedEvent":
        return WorkflowCreatedEvent(**payload)
    elif event_type == "StateTransitionedEvent":
        return StateTransitionedEvent(**payload)
    elif event_type == "WorkflowFailedEvent":
        return WorkflowFailedEvent(**payload)
    else:
        return DomainEvent() # Fallback

class SnapshotRepository:
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        
    def _get_path(self, workflow_id: str) -> Path:
        return self.workspace_path / ".karsa" / "workflows" / workflow_id / "snapshot.json"
        
    def save(self, snapshot: WorkflowSnapshot):
        path = self._get_path(snapshot.workflow_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "workflow_id": snapshot.workflow_id,
            "state": snapshot.state.value,
            "data": snapshot.data,
            "schema_version": snapshot.schema_version,
            "last_sequence_number": snapshot.last_sequence_number
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            
    def load(self, workflow_id: str) -> Optional[WorkflowSnapshot]:
        path = self._get_path(workflow_id)
        if not path.exists():
            return None
            
        with open(path, "r") as f:
            data = json.load(f)
            return WorkflowSnapshot(
                workflow_id=data["workflow_id"],
                state=WorkflowState(data["state"]),
                data=data.get("data", {}),
                schema_version=data.get("schema_version", 1),
                last_sequence_number=data.get("last_sequence_number", 0)
            )

class EventJournalRepository:
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        
    def _get_path(self, workflow_id: str) -> Path:
        return self.workspace_path / ".karsa" / "workflows" / workflow_id / "events.jsonl"
        
    def append(self, workflow_id: str, event: DomainEvent):
        path = self._get_path(workflow_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        event_data = serialize_event(event)
        with open(path, "a") as f:
            f.write(json.dumps(event_data) + "\n")
            
    def load(self, workflow_id: str) -> List[DomainEvent]:
        path = self._get_path(workflow_id)
        if not path.exists():
            return []
            
        events = []
        with open(path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                events.append(deserialize_event(data))
        return events
