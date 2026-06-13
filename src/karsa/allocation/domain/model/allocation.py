from enum import Enum
from dataclasses import dataclass
from typing import Optional

class AllocationState(Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"

class InvalidAllocationStateTransitionError(Exception):
    pass

class LiquidityConstraintViolationError(Exception):
    pass

@dataclass
class LiquidityConstraint:
    max_adv_participation: float  # e.g., 0.10 for 10%
    max_days_to_liquidate: float  # e.g., 5.0 days
    
    def validate(self) -> None:
        if self.max_adv_participation <= 0.0 or self.max_adv_participation > 1.0:
            raise LiquidityConstraintViolationError("max_adv_participation must be between 0.0 and 1.0")
        if self.max_days_to_liquidate <= 0.0:
            raise LiquidityConstraintViolationError("max_days_to_liquidate must be greater than 0.0")

@dataclass
class RiskBudget:
    volatility_budget: float
    drawdown_limit: float
    liquidity_constraint: LiquidityConstraint

class RiskAllocation:
    def __init__(self, allocation_id: str, thesis_id: str, risk_budget: RiskBudget):
        self.allocation_id = allocation_id
        self.thesis_id = thesis_id
        self.risk_budget = risk_budget
        self.state = AllocationState.PENDING
        
        self.risk_budget.liquidity_constraint.validate()
        
    def activate(self) -> None:
        if self.state not in [AllocationState.PENDING, AllocationState.SUSPENDED]:
            raise InvalidAllocationStateTransitionError(f"Cannot transition to ACTIVE from {self.state.value}")
        self.state = AllocationState.ACTIVE
        
    def suspend(self) -> None:
        if self.state not in [AllocationState.PENDING, AllocationState.ACTIVE]:
            raise InvalidAllocationStateTransitionError(f"Cannot transition to SUSPENDED from {self.state.value}")
        self.state = AllocationState.SUSPENDED
        
    def terminate(self) -> None:
        if self.state not in [AllocationState.PENDING, AllocationState.ACTIVE, AllocationState.SUSPENDED]:
            raise InvalidAllocationStateTransitionError(f"Cannot transition to TERMINATED from {self.state.value}")
        self.state = AllocationState.TERMINATED

    def scale_volatility_budget(self, realized_volatility: float) -> None:
        """
        Scales down the volatility budget if realized volatility exceeds expectations.
        Does not change state.
        """
        if self.state not in [AllocationState.PENDING, AllocationState.ACTIVE]:
            return
            
        if realized_volatility > self.risk_budget.volatility_budget:
            # Simple scaling logic: inversely proportional to the realized volatility excess.
            # (target_vol / realized_vol) * target_vol
            scaling_factor = self.risk_budget.volatility_budget / realized_volatility
            self.risk_budget.volatility_budget = self.risk_budget.volatility_budget * scaling_factor
            
    def evaluate_drawdown(self, current_drawdown: float) -> None:
        """
        Evaluates current drawdown against the limit.
        If the drawdown limit is breached (current_drawdown > drawdown_limit), suspends the allocation.
        """
        if self.state not in [AllocationState.PENDING, AllocationState.ACTIVE]:
            return
            
        # Assuming current_drawdown is a positive float representing percentage drawdown, e.g., 0.15 for 15%
        if current_drawdown >= self.risk_budget.drawdown_limit:
            self.suspend()
