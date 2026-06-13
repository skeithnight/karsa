import pytest
from karsa.allocation.domain.model.allocation import (
    RiskAllocation,
    RiskBudget,
    LiquidityConstraint,
    AllocationState,
    InvalidAllocationStateTransitionError,
    LiquidityConstraintViolationError
)

def create_valid_budget():
    liquidity = LiquidityConstraint(max_adv_participation=0.1, max_days_to_liquidate=5.0)
    return RiskBudget(volatility_budget=0.15, drawdown_limit=0.10, liquidity_constraint=liquidity)

def test_allocation_initial_state():
    budget = create_valid_budget()
    allocation = RiskAllocation("A-1", "T-1", budget)
    assert allocation.state == AllocationState.PENDING

def test_transition_pending_to_active():
    budget = create_valid_budget()
    allocation = RiskAllocation("A-1", "T-1", budget)
    allocation.activate()
    assert allocation.state == AllocationState.ACTIVE

def test_transition_active_to_suspended():
    budget = create_valid_budget()
    allocation = RiskAllocation("A-1", "T-1", budget)
    allocation.activate()
    allocation.suspend()
    assert allocation.state == AllocationState.SUSPENDED

def test_transition_active_to_terminated():
    budget = create_valid_budget()
    allocation = RiskAllocation("A-1", "T-1", budget)
    allocation.activate()
    allocation.terminate()
    assert allocation.state == AllocationState.TERMINATED

def test_transition_suspended_to_active():
    budget = create_valid_budget()
    allocation = RiskAllocation("A-1", "T-1", budget)
    allocation.activate()
    allocation.suspend()
    allocation.activate()
    assert allocation.state == AllocationState.ACTIVE

def test_transition_suspended_to_terminated():
    budget = create_valid_budget()
    allocation = RiskAllocation("A-1", "T-1", budget)
    allocation.activate()
    allocation.suspend()
    allocation.terminate()
    assert allocation.state == AllocationState.TERMINATED

def test_invalid_transition_terminated_to_active():
    budget = create_valid_budget()
    allocation = RiskAllocation("A-1", "T-1", budget)
    allocation.terminate()
    with pytest.raises(InvalidAllocationStateTransitionError):
        allocation.activate()

def test_invalid_transition_terminated_to_suspended():
    budget = create_valid_budget()
    allocation = RiskAllocation("A-1", "T-1", budget)
    allocation.terminate()
    with pytest.raises(InvalidAllocationStateTransitionError):
        allocation.suspend()

def test_invalid_transition_terminated_to_terminated():
    budget = create_valid_budget()
    allocation = RiskAllocation("A-1", "T-1", budget)
    allocation.terminate()
    with pytest.raises(InvalidAllocationStateTransitionError):
        allocation.terminate()

def test_liquidity_constraint_validation():
    with pytest.raises(LiquidityConstraintViolationError):
        liquidity = LiquidityConstraint(max_adv_participation=1.5, max_days_to_liquidate=5.0)
        budget = RiskBudget(volatility_budget=0.15, drawdown_limit=0.10, liquidity_constraint=liquidity)
        RiskAllocation("A-1", "T-1", budget)
        
    with pytest.raises(LiquidityConstraintViolationError):
        liquidity = LiquidityConstraint(max_adv_participation=0.1, max_days_to_liquidate=-2.0)
        budget = RiskBudget(volatility_budget=0.15, drawdown_limit=0.10, liquidity_constraint=liquidity)
        RiskAllocation("A-1", "T-1", budget)

def test_scale_volatility_budget_does_not_mutate_state():
    budget = create_valid_budget()
    allocation = RiskAllocation("A-1", "T-1", budget)
    allocation.activate()
    
    realized_vol = 0.30
    allocation.scale_volatility_budget(realized_vol)
    
    # Expected scaling factor: 0.15 / 0.30 = 0.5
    # New budget: 0.15 * 0.5 = 0.075
    assert allocation.risk_budget.volatility_budget == pytest.approx(0.075)
    # Proving budget scaling does not mutate lifecycle state
    assert allocation.state == AllocationState.ACTIVE

def test_scale_volatility_no_action_on_low_vol():
    budget = create_valid_budget()
    allocation = RiskAllocation("A-1", "T-1", budget)
    allocation.activate()
    
    initial_vol = budget.volatility_budget  # 0.15
    allocation.scale_volatility_budget(0.10)
    
    assert allocation.risk_budget.volatility_budget == initial_vol

def test_evaluate_drawdown_suspends_on_breach():
    budget = create_valid_budget()
    allocation = RiskAllocation("A-1", "T-1", budget)
    allocation.activate()
    
    # drawdown_limit is 0.10
    allocation.evaluate_drawdown(0.12)
    assert allocation.state == AllocationState.SUSPENDED

def test_evaluate_drawdown_no_action_below_limit():
    budget = create_valid_budget()
    allocation = RiskAllocation("A-1", "T-1", budget)
    allocation.activate()
    
    allocation.evaluate_drawdown(0.05)
    assert allocation.state == AllocationState.ACTIVE
