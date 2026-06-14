from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict
from karsa.decision_journal.value_objects import DecisionContextSnapshot

@dataclass
class ActiveLeafProjection:
    root_decision_id: str
    active_leaf_decision_id: str
    version: int
    updated_at: datetime

@dataclass
class ReasoningLineageProjection:
    root_decision_id: str
    nodes: List[str]
    parent_map: Dict[str, str]

@dataclass
class ReplayProjection:
    decision_id: str
    context_snapshot: DecisionContextSnapshot
    verified: bool

@dataclass
class AuditProjection:
    decision_id: str
    is_immutable: bool
    trigger_verified: bool
