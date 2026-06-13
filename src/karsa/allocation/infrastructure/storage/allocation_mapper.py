from karsa.allocation.domain.model.allocation import (
    RiskAllocation,
    RiskBudget,
    LiquidityConstraint,
    AllocationState
)
from karsa.allocation.infrastructure.storage.allocation_records import (
    RiskAllocationRecord,
    RiskBudgetRecord,
    LiquidityConstraintRecord
)

class AllocationMapper:
    @staticmethod
    def to_record(allocation: RiskAllocation) -> RiskAllocationRecord:
        liquidity_record = LiquidityConstraintRecord(
            max_adv_participation=allocation.risk_budget.liquidity_constraint.max_adv_participation,
            max_days_to_liquidate=allocation.risk_budget.liquidity_constraint.max_days_to_liquidate
        )
        
        budget_record = RiskBudgetRecord(
            volatility_budget=allocation.risk_budget.volatility_budget,
            drawdown_limit=allocation.risk_budget.drawdown_limit,
            liquidity_constraint=liquidity_record
        )
        
        return RiskAllocationRecord(
            allocation_id=allocation.allocation_id,
            thesis_id=allocation.thesis_id,
            state=allocation.state.value,
            risk_budget=budget_record
        )

    @staticmethod
    def to_domain(record: RiskAllocationRecord) -> RiskAllocation:
        liquidity = LiquidityConstraint(
            max_adv_participation=record.risk_budget.liquidity_constraint.max_adv_participation,
            max_days_to_liquidate=record.risk_budget.liquidity_constraint.max_days_to_liquidate
        )
        
        budget = RiskBudget(
            volatility_budget=record.risk_budget.volatility_budget,
            drawdown_limit=record.risk_budget.drawdown_limit,
            liquidity_constraint=liquidity
        )
        
        allocation = RiskAllocation(
            allocation_id=record.allocation_id,
            thesis_id=record.thesis_id,
            risk_budget=budget
        )
        # Override state mapping bypasses PENDING constructor invariant
        allocation.state = AllocationState(record.state)
        
        return allocation
