from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

class WorkflowState(Enum):
    IDEA = "IDEA"
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    REVISE = "REVISE"
    APPROVED = "APPROVED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"

@dataclass(frozen=True)
class GovernancePolicy:
    max_workflow_cost: float = 0.0
    max_workflow_tokens: int = 0
    max_review_cycles: int = 0
    max_cycle_cost: float = 0.0

@dataclass(frozen=True)
class GovernancePolicySnapshot:
    policy_version: str
    policy_hash: str
    max_workflow_cost: float
    max_workflow_tokens: int
    max_review_cycles: int
    max_cycle_cost: float

@dataclass(frozen=True)
class ViolationContext:
    limit_name: str
    limit_value: float
    actual_value: float

@dataclass(frozen=True)
class GovernanceDecision:
    workflow_id: str
    review_cycle_id: str
    execution_id: str
    sequence_number: int
    decision_type: str
    reason: str
    violation_context: Optional[ViolationContext] = None

@dataclass
class WorkflowSnapshot:
    workflow_id: str
    state: WorkflowState
    policy: Optional[GovernancePolicySnapshot] = None
    data: Dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1
    last_sequence_number: int = 0
@dataclass
class PricingRegistryEntry:
    model_id: str
    base_input_rate: float
    base_output_rate: float
    reasoning_output_rate: float = 0.0
    cached_input_rate: float = 0.0
    tool_call_rate: float = 0.0

@dataclass
class ExecutionMetrics:
    execution_id: str
    review_cycle_id: str
    agent_name: str
    model: str
    provider: str
    duration_ms: int
    input_tokens: int
    output_tokens: int
    token_estimation_confidence: str
    cost_usd: float
    status: str
    timestamp: str

@dataclass
class AgentMetrics:
    agent_name: str
    total_executions: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0

@dataclass
class ReviewCycleMetrics:
    review_cycle_id: str
    total_executions: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0

@dataclass
class WorkflowMetrics:
    workflow_id: str
    total_executions: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_duration_ms: int = 0
    status: str = "PENDING"
