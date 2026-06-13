from dataclasses import dataclass

@dataclass
class LiquidityConstraintRecord:
    max_adv_participation: float
    max_days_to_liquidate: float

@dataclass
class RiskBudgetRecord:
    volatility_budget: float
    drawdown_limit: float
    liquidity_constraint: LiquidityConstraintRecord

@dataclass
class RiskAllocationRecord:
    allocation_id: str
    thesis_id: str
    state: str
    risk_budget: RiskBudgetRecord
