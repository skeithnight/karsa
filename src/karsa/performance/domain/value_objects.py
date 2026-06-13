from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class DecisionPerformanceIdentity:
    decision_id: str
    outcome_sequence_id: int
    attribution_generation: int

@dataclass(frozen=True)
class RiskMetrics:
    cumulative_gross_pnl: Decimal
    cumulative_net_pnl: Decimal
    max_drawdown: Decimal
    volatility_proxy: Decimal
    sharpe_proxy: Decimal

@dataclass(frozen=True)
class CalibrationMetrics:
    stated_confidence: Decimal
    brier_score: Decimal
    hit_rate: Decimal
