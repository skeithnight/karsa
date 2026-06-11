import json
from dataclasses import dataclass, asdict
from pathlib import Path
from pathlib import Path
from typing import Callable, Dict, List
from karsa.domain.models import ExecutionMetrics, WorkflowState, GovernanceDecision

@dataclass
class DomainEvent:
    pass

@dataclass
class ExecutionCompletedEvent(DomainEvent):
    metrics: ExecutionMetrics

@dataclass
class WorkflowCreatedEvent(DomainEvent):
    workflow_id: str
    sequence_number: int = 0

@dataclass
class StateTransitionedEvent(DomainEvent):
    workflow_id: str
    previous_state: WorkflowState
    new_state: WorkflowState
    reason: str = ""
    sequence_number: int = 0

@dataclass
class WorkflowFailedEvent(DomainEvent):
    workflow_id: str
    reason: str
    sequence_number: int = 0

@dataclass
class WorkflowAbortedEvent(DomainEvent):
    workflow_id: str
    reason: str
    sequence_number: int = 0

@dataclass
class GovernanceDecisionEvent(DomainEvent):
    decision: GovernanceDecision
    sequence_number: int = 0

class EventBus:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._subscribers = {}
            cls._instance._events_log_file = None
        return cls._instance

    def initialize(self, events_log_file: Path):
        self._events_log_file = events_log_file
        if not self._events_log_file.exists():
            self._events_log_file.parent.mkdir(parents=True, exist_ok=True)
            self._events_log_file.touch()

    def subscribe(self, event_type: type, handler: Callable[[DomainEvent], None]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def publish(self, event: DomainEvent):
        event_type = type(event)
        
        # Persist event
        if self._events_log_file:
            with open(self._events_log_file, "a") as f:
                event_data = {
                    "event_type": event_type.__name__,
                    "payload": asdict(event)
                }
                f.write(json.dumps(event_data) + "\n")
                
        # Synchronous execution
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                handler(event)
