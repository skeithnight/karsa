import pytest
import copy
import hashlib
from karsa.allocation.domain.model.allocation import RiskAllocation, RiskBudget, LiquidityConstraint
from karsa.portfolio.domain.model.portfolio import (
    Portfolio, TargetPosition, CashTarget, RegimeState, AllocationPortfolioMapping, Position, ExposureMetrics, DriftMetrics
)
from karsa.portfolio.domain.service.rebalancing_engine import RebalancingEngine

@pytest.fixture
def engine():
    return RebalancingEngine()

@pytest.fixture
def empty_portfolio():
    return Portfolio("P-1")

@pytest.fixture
def regime():
    return RegimeState("BULL", "LOW", "HIGH", 0.9)

@pytest.fixture
def cash_target():
    return CashTarget(0.10)

def create_allocation(a_id, t_id):
    budget = RiskBudget(0.1, 0.1, LiquidityConstraint(0.1, 5.0))
    return RiskAllocation(a_id, t_id, budget)

def test_exposure_calculation_no_negative(engine, empty_portfolio):
    empty_portfolio.add_position(Position("POS", "P-1", "AAPL", 100, 100, 10000))
    exposure = engine.calculate_exposure(empty_portfolio)
    assert exposure.gross_exposure >= 0
    assert exposure.net_exposure >= 0
    assert exposure.concentration_exposure >= 0

def test_drift_calculation(engine, empty_portfolio):
    empty_portfolio.add_position(Position("POS", "P-1", "AAPL", 100, 100, 10000))
    targets = frozenset([TargetPosition("AAPL", 0.8), TargetPosition("MSFT", 0.2)])
    drifts = engine.calculate_drift(empty_portfolio, targets)
    
    aapl_drift = next(d for d in drifts if d.symbol == "AAPL")
    msft_drift = next(d for d in drifts if d.symbol == "MSFT")
    
    assert aapl_drift.actual_weight == 1.0
    assert aapl_drift.target_weight == 0.8
    assert msft_drift.actual_weight == 0.0
    assert msft_drift.target_weight == 0.2

def test_constraint_evaluation(engine):
    cash = CashTarget(0.1)
    exp_pass = ExposureMetrics(1.0, 1.0, 0.5, 0.15, 1.0)
    is_valid, viol = engine.evaluate_constraints(exp_pass, cash, 100000)
    assert is_valid is True

def test_functional_purity(engine, regime, cash_target):
    p = Portfolio("P-1")
    p.add_position(Position("POS", "P-1", "AAPL", 100, 100, 10000))
    p_copy = copy.deepcopy(p)
    
    a1 = create_allocation("A-1", "T-1")
    m1 = AllocationPortfolioMapping("A-1", "P-1", 1.0)
    
    res = engine.rebalance(p, [a1], [m1], cash_target, 100000, regime)
    
    assert p.positions[0].symbol == p_copy.positions[0].symbol
    assert p.state == p_copy.state

def test_deterministic_target_generation(engine, regime, cash_target):
    p = Portfolio("P-1")
    a1 = create_allocation("A-1", "T-1")
    m1 = AllocationPortfolioMapping("A-1", "P-1", 1.0)
    
    res1 = engine.rebalance(p, [a1], [m1], cash_target, 100000, regime)
    res2 = engine.rebalance(p, [a1], [m1], cash_target, 100000, regime)
    
    # Identical inputs must always produce identical snapshot identifiers (SHA-256)
    assert res1.target_snapshot.snapshot_id == res2.target_snapshot.snapshot_id
    assert res1.target_snapshot.target_positions == res2.target_snapshot.target_positions
    assert "SNAP_P-1_" in res1.target_snapshot.snapshot_id

def test_deterministic_trade_intent_ordering(engine):
    drifts = [DriftMetrics("Z", 0.5, 0.3), DriftMetrics("A", 0.1, 0.4), DriftMetrics("M", 0.1, 0.4)]
    intents = engine.generate_trade_intents("P-1", "S-1", drifts)
    # Must be alphabetically sorted by symbol: A, M, Z
    assert intents[0].symbol == "A"
    assert intents[1].symbol == "M"
    assert intents[2].symbol == "Z"

def test_deterministic_decision_generation(engine, regime, cash_target, empty_portfolio):
    a1 = create_allocation("A-1", "T-1")
    a2 = create_allocation("A-2", "T-2")
    m1 = AllocationPortfolioMapping("A-1", "P-1", 1.0)
    m2 = AllocationPortfolioMapping("A-2", "P-1", 1.0)
    
    res1 = engine.rebalance(empty_portfolio, [a1, a2], [m1, m2], cash_target, 100000, regime)
    res2 = engine.rebalance(empty_portfolio, [a1, a2], [m1, m2], cash_target, 100000, regime)
    
    assert res1.decision.decision_id == res2.decision.decision_id
    assert res1.decision.expected_outcome == res2.decision.expected_outcome
    # Ensure stable ordering in lists
    assert res1.decision.expected_outcome["target_symbols"] == "['SYM_T-1', 'SYM_T-2']"
