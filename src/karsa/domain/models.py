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

@dataclass
class WorkflowSnapshot:
    workflow_id: str
    state: WorkflowState
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
