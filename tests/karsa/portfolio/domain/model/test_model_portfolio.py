import pytest
from datetime import datetime
from karsa.portfolio.domain.model.portfolio import (
    Portfolio, PortfolioState, InvalidPortfolioStateTransitionError, ValidationException,
    Position, TargetPosition, PortfolioTargetSnapshot, ExposureMetrics, CashTarget,
    PortfolioSnapshot, PortfolioDecision, AllocationPortfolioMapping, TradeIntent, RegimeState
)

def test_portfolio_lifecycle_transitions():
    p = Portfolio("P-1")
    assert p.state == PortfolioState.INITIALIZING
    
    p.activate()
    assert p.state == PortfolioState.ACTIVE
    
    p.rebalance()
    assert p.state == PortfolioState.REBALANCING
    
    p.activate()
    assert p.state == PortfolioState.ACTIVE
    
    p.suspend()
    assert p.state == PortfolioState.SUSPENDED
    
    p.liquidate()
    assert p.state == PortfolioState.LIQUIDATING

def test_invalid_lifecycle_transitions():
    p = Portfolio("P-1")
    with pytest.raises(InvalidPortfolioStateTransitionError):
        p.rebalance() # INITIALIZING -> REBALANCING is invalid
        
    p.activate()
    p.liquidate()
    with pytest.raises(InvalidPortfolioStateTransitionError):
        p.activate() # LIQUIDATING -> ACTIVE is invalid
        
    with pytest.raises(InvalidPortfolioStateTransitionError):
        p.rebalance() # LIQUIDATING -> REBALANCING is invalid

def test_portfolio_target_snapshot_immutability():
    positions = frozenset([TargetPosition("AAPL", 0.5)])
    snapshot = PortfolioTargetSnapshot("S-1", "P-1", 1, positions)
    
    with pytest.raises(Exception):
        snapshot.version = 2
    with pytest.raises(Exception):
        snapshot.portfolio_id = "P-2"

def test_portfolio_decision_immutability():
    decision = PortfolioDecision(
        "D-1", "P-1", "S-1", datetime.utcnow(),
        {"trend": "stable"}, {"max_weight": "0.10"}, {"alpha": "0.05"}, [{"option": "none"}], "because"
    )
    with pytest.raises(Exception):
        decision.portfolio_id = "P-2"

def test_allocation_portfolio_mapping_validation():
    with pytest.raises(ValidationException):
        AllocationPortfolioMapping("A-1", "P-1", 0.0)
    
    with pytest.raises(ValidationException):
        AllocationPortfolioMapping("A-1", "P-1", -0.5)
        
    m = AllocationPortfolioMapping("A-1", "P-1", 1.0)
    assert m.allocation_weight == 1.0

def test_cash_target_validation():
    with pytest.raises(ValidationException):
        CashTarget(-0.1)
        
    with pytest.raises(ValidationException):
        CashTarget(1.1)
        
    c = CashTarget(0.5)
    assert c.target_cash_percentage == 0.5

def test_exposure_metrics_validation():
    with pytest.raises(ValidationException):
        ExposureMetrics(-0.1, 0, 0, 0, 0)
        
    with pytest.raises(ValidationException):
        ExposureMetrics(0, -0.1, 0, 0, 0)

    e = ExposureMetrics(1.0, 0.5, 0.2, 0.1, 1.2)
    assert e.gross_exposure == 1.0

def test_regime_state_validation():
    with pytest.raises(ValidationException):
        RegimeState("BULL", "HIGH", "LOW", -0.1)
        
    with pytest.raises(ValidationException):
        RegimeState("BULL", "HIGH", "LOW", 1.1)
        
    r = RegimeState("BULL", "HIGH", "LOW", 0.82)
    assert r.confidence == 0.82

def test_trade_intent_creation():
    intent = TradeIntent("I-1", "P-1", "S-1", "AAPL", "BUY", 0.1, "rebalance")
    assert intent.action == "BUY"
    assert intent.target_weight == 0.1

def test_position_creation():
    pos = Position("POS-1", "P-1", "AAPL", 100, 150.0, 16000.0)
    assert pos.symbol == "AAPL"

def test_portfolio_aggregate_invariants():
    p = Portfolio("P-1")
    pos = Position("POS-1", "P-1", "AAPL", 100, 150.0, 16000.0)
    p.add_position(pos)
    assert len(p.positions) == 1
    
    metrics = ExposureMetrics(1.5, 0.8, 0.2, 0.1, 1.5)
    p.update_exposure_metrics(metrics)
    assert p.exposure_metrics.gross_exposure == 1.5

def test_nm_mapping_support():
    # Showing N:M mapping objects can be created properly without conflict
    map1 = AllocationPortfolioMapping("A-1", "P-1", 0.5)
    map2 = AllocationPortfolioMapping("A-1", "P-2", 0.5)
    map3 = AllocationPortfolioMapping("A-2", "P-1", 1.0)
    
    assert map1.allocation_id == map2.allocation_id
    assert map1.portfolio_id != map2.portfolio_id
    assert map1.portfolio_id == map3.portfolio_id
