from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ExecutionOutcomeContract:
    """
    Future-facing contract defining the shape of an execution outcome
    returned from WP-14 Execution Engine.
    """
    decision_id: str
    intent_id: str
    execution_status: str  # e.g., 'FILLED', 'PARTIAL', 'FAILED'
    requested_quantity: float
    filled_quantity: float
    requested_price: Optional[float]
    average_fill_price: float
    fees: float
    slippage: float
    executed_at: str
    broker_reference: Optional[str]
