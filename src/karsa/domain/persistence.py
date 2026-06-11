import json
import os
from pathlib import Path
from typing import List, Optional, Any, Dict, Callable
from karsa.domain.events import (
    DomainEvent, WorkflowCreatedEvent, StateTransitionedEvent, WorkflowFailedEvent, 
    WorkflowAbortedEvent, GovernanceDecisionEvent, ArtifactPersistedEvent, UserOverrideEvent,
    ExecutionCheckpointEvent, ReviewCycleStartedEvent, ReviewCycleCompletedEvent, EscalationTriggeredEvent
)
from karsa.domain.models import ViolationContext, GovernanceDecision, GovernancePolicySnapshot, WorkflowSnapshot, WorkflowState

class CorruptedJournalError(Exception):
    pass

def serialize_event(event: DomainEvent) -> Dict[str, Any]:
    # Handle enums
    payload = {}
    for k, v in event.__dict__.items():
        if k == "schema_version":
            continue
        if isinstance(v, WorkflowState):
            payload[k] = v.value
        elif isinstance(v, GovernanceDecision):
            decision_dict = v.__dict__.copy()
            if v.violation_context:
                decision_dict["violation_context"] = v.violation_context.__dict__
            payload[k] = decision_dict
        else:
            payload[k] = v
    return {
        "event_type": type(event).__name__,
        "schema_version": getattr(event, "schema_version", 1),
        "payload": payload
    }

def deserialize_event(data: Dict[str, Any]) -> DomainEvent:
    event_type = data.get("event_type")
    payload = data.get("payload", {})
    schema_version = data.get("schema_version", 1)
    
    # Rehydrate Enum
    if "previous_state" in payload:
        payload["previous_state"] = WorkflowState(payload["previous_state"])
    if "new_state" in payload:
        payload["new_state"] = WorkflowState(payload["new_state"])
        
    if event_type == "WorkflowCreatedEvent":
        return WorkflowCreatedEvent(schema_version=schema_version, **payload)
    elif event_type == "StateTransitionedEvent":
        return StateTransitionedEvent(schema_version=schema_version, **payload)
    elif event_type == "WorkflowFailedEvent":
        return WorkflowFailedEvent(schema_version=schema_version, **payload)
    elif event_type == "WorkflowAbortedEvent":
        return WorkflowAbortedEvent(schema_version=schema_version, **payload)
    elif event_type == "GovernanceDecisionEvent":
        decision_data = payload["decision"]
        if "violation_context" in decision_data and decision_data["violation_context"]:
            decision_data["violation_context"] = ViolationContext(**decision_data["violation_context"])
        payload["decision"] = GovernanceDecision(**decision_data)
        return GovernanceDecisionEvent(schema_version=schema_version, **payload)
    elif event_type == "ArtifactPersistedEvent":
        return ArtifactPersistedEvent(schema_version=schema_version, **payload)
    elif event_type == "UserOverrideEvent":
        return UserOverrideEvent(schema_version=schema_version, **payload)
    elif event_type == "ExecutionCheckpointEvent":
        return ExecutionCheckpointEvent(schema_version=schema_version, **payload)
    elif event_type == "ReviewCycleStartedEvent":
        return ReviewCycleStartedEvent(schema_version=schema_version, **payload)
    elif event_type == "ReviewCycleCompletedEvent":
        return ReviewCycleCompletedEvent(schema_version=schema_version, **payload)
    elif event_type == "EscalationTriggeredEvent":
        return EscalationTriggeredEvent(schema_version=schema_version, **payload)
    else:
        return DomainEvent(schema_version=schema_version) # Fallback

class SnapshotRepository:
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        
    def _get_path(self, workflow_id: str) -> Path:
        return self.workspace_path / ".karsa" / "workflows" / workflow_id / "snapshot.json"
        
    def save(self, snapshot: WorkflowSnapshot, verify_lock: Callable[[str], None] = None):
        if verify_lock:
            verify_lock(snapshot.workflow_id)
            
        path = self._get_path(snapshot.workflow_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "workflow_id": snapshot.workflow_id,
            "state": snapshot.state.value,
            "policy": snapshot.policy.__dict__ if snapshot.policy else None,
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
            policy_data = data.get("policy")
            policy = GovernancePolicySnapshot(**policy_data) if policy_data else None
            return WorkflowSnapshot(
                workflow_id=data["workflow_id"],
                state=WorkflowState(data["state"]),
                policy=policy,
                data=data.get("data", {}),
                schema_version=data.get("schema_version", 1),
                last_sequence_number=data.get("last_sequence_number", 0)
            )

class EventJournalRepository:
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        
    def _get_path(self, workflow_id: str) -> Path:
        return self.workspace_path / ".karsa" / "workflows" / workflow_id / "events.jsonl"
        
    def append(self, workflow_id: str, event: DomainEvent, verify_lock: Callable[[str], None] = None):
        if verify_lock:
            verify_lock(workflow_id)
            
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
                try:
                    data = json.loads(line)
                    events.append(deserialize_event(data))
                except json.JSONDecodeError as e:
                    raise CorruptedJournalError(f"Failed to decode journal line: {e}")
        return events
