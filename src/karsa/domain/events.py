import json
from dataclasses import dataclass, asdict
from pathlib import Path
from pathlib import Path
from typing import Callable, Dict, List
from karsa.domain.models import ExecutionMetrics, WorkflowState, GovernanceDecision

@dataclass
class DomainEvent:
    schema_version: int = 1

@dataclass
class ExecutionCompletedEvent(DomainEvent):
    metrics: ExecutionMetrics = None
    sequence_number: int = 0

@dataclass
class WorkflowCreatedEvent(DomainEvent):
    workflow_id: str = ""
    sequence_number: int = 0

@dataclass
class StateTransitionedEvent(DomainEvent):
    workflow_id: str = ""
    previous_state: WorkflowState = None
    new_state: WorkflowState = None
    reason: str = ""
    sequence_number: int = 0

@dataclass
class WorkflowFailedEvent(DomainEvent):
    workflow_id: str = ""
    reason: str = ""
    sequence_number: int = 0

@dataclass
class WorkflowAbortedEvent(DomainEvent):
    workflow_id: str = ""
    reason: str = ""
    sequence_number: int = 0

@dataclass
class GovernanceDecisionEvent(DomainEvent):
    decision: GovernanceDecision = None
    sequence_number: int = 0

@dataclass
class ArtifactPersistedEvent(DomainEvent):
    artifact_id: str = ""
    target_path: str = ""
    sha256_hash: str = ""
    sequence_number: int = 0

@dataclass
class UserOverrideEvent(DomainEvent):
    artifact_name: str = ""
    new_version_hash: str = ""
    sequence_number: int = 0

@dataclass
class ExecutionCheckpointEvent(DomainEvent):
    cycle_id: int = 0
    sub_task_name: str = ""
    artifact_version_hash: str = ""
    accumulated_cost: float = 0.0
    accumulated_tokens: int = 0
    sequence_number: int = 0

@dataclass
class ReviewCycleStartedEvent(DomainEvent):
    cycle_id: int = 0
    sequence_number: int = 0

@dataclass
class ReviewCycleCompletedEvent(DomainEvent):
    cycle_id: int = 0
    convergence_score: float = 0.0
    sequence_number: int = 0

@dataclass
class EscalationTriggeredEvent(DomainEvent):
    cycle_id: int = 0
    divergence_reason: str = ""
    sequence_number: int = 0

