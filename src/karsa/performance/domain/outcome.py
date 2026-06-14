from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Dict

@dataclass(frozen=True)
class ExecutionOutcome:
    decision_id: str
    outcome_id: str
    target_type: str                     # e.g., "WORKER", "THESIS_VERSION"
    target_id: str
    actual_return_bps: Decimal
    drawdown_pct: Decimal
    is_success: bool
    parameter_deviation: Decimal
    latency_ms: int
    token_count: int
    slippage_bps: Decimal
    benchmark_returns: Dict[str, Decimal] # e.g., {"SPY": Decimal("10.5"), "QQQ": Decimal("15.2")}
    regime_id: str
    resolved_at: datetime
