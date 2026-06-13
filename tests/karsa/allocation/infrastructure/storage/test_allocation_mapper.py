import pytest
from karsa.allocation.domain.model.allocation import (
    RiskAllocation, RiskBudget, LiquidityConstraint, AllocationState
)
from karsa.allocation.infrastructure.storage.allocation_mapper import AllocationMapper

def test_mapper_roundtrip():
    liquidity = LiquidityConstraint(max_adv_participation=0.1, max_days_to_liquidate=5.0)
    budget = RiskBudget(volatility_budget=0.15, drawdown_limit=0.10, liquidity_constraint=liquidity)
    allocation = RiskAllocation("A-1", "T-1", budget)
    allocation.activate()
    allocation.suspend()
    
    # Domain -> Record
    record = AllocationMapper.to_record(allocation)
    assert record.allocation_id == "A-1"
    assert record.thesis_id == "T-1"
    assert record.state == "SUSPENDED"
    assert record.risk_budget.volatility_budget == 0.15
    assert record.risk_budget.drawdown_limit == 0.10
    assert record.risk_budget.liquidity_constraint.max_adv_participation == 0.1
    assert record.risk_budget.liquidity_constraint.max_days_to_liquidate == 5.0
    
    # Record -> Domain
    restored = AllocationMapper.to_domain(record)
    assert restored.allocation_id == "A-1"
    assert restored.thesis_id == "T-1"
    assert restored.state == AllocationState.SUSPENDED
    assert restored.risk_budget.volatility_budget == 0.15
    assert restored.risk_budget.drawdown_limit == 0.10
    assert restored.risk_budget.liquidity_constraint.max_adv_participation == 0.1
    assert restored.risk_budget.liquidity_constraint.max_days_to_liquidate == 5.0
