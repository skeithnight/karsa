import os
import json
import pytest
import shutil
from decimal import Decimal
from datetime import datetime, timezone
from karsa.portfolio import (
    PortfolioAggregate, PositionAggregate, CashLedgerAggregate, ValuationAggregate,
    PositionStatus, HoldingLot, AssetExposure, BenchmarkReference, PortfolioSnapshot,
    HoldingsUpdatedEvent, CashUpdatedEvent, PositionOpenedEvent, PositionClosedEvent,
    PortfolioValuationCalculatedEvent, ExposureCalculatedEvent,
    InMemoryPortfolioRepository, InMemoryPositionRepository, InMemoryCashLedgerRepository, InMemoryValuationRepository,
    FilePortfolioRepository, FilePositionRepository, FileCashLedgerRepository, FileValuationRepository,
    ConcurrencyConflictError, DatabaseImmutabilityError, InsufficientFundsError,
    BenchmarkRegistryService, ExposureCalculationService, PortfolioValuationService, PortfolioProjectionService,
    PortfolioIntegrationPort, PerformancePortImpl, RiskEnginePortImpl,
    PortfolioAPI
)

# 1. Domain Tests
def test_portfolio_aggregate_immutability():
    p = PortfolioAggregate("port-1", "owner-1")
    assert p.portfolio_id == "port-1"
    with pytest.raises(TypeError):
        p.portfolio_id = "port-2"

def test_position_aggregate_lifecycle():
    pos = PositionAggregate("pos-1", "port-1", "AAPL", Decimal("10"), Decimal("150"))
    assert pos.status == PositionStatus.OPEN
    assert pos.aggregate_version == 1
    
    # Buy 5 units of AAPL at 160
    pos.update_position(Decimal("5"), Decimal("160"), "lot-2", datetime.now())
    assert pos.units == Decimal("15")
    # (10 * 150 + 5 * 160) / 15 = 2300 / 15 = 153.3333...
    assert pos.average_cost == Decimal("2300") / Decimal("15")
    assert pos.aggregate_version == 2
    
    # Sell 15 units of AAPL
    pos.update_position(Decimal("-15"), Decimal("170"), "lot-3", datetime.now())
    assert pos.units == Decimal("0")
    assert pos.status == PositionStatus.CLOSED
    assert pos.aggregate_version == 3

def test_cash_ledger_aggregate():
    cash = CashLedgerAggregate("port-1", Decimal("1000"), Decimal("0"))
    cash.adjust_cash(Decimal("500"))
    assert cash.available_balance == Decimal("1500")
    
    with pytest.raises(InsufficientFundsError):
        cash.adjust_cash(Decimal("-2000"))

def test_valuation_aggregate_immutability():
    val = ValuationAggregate("val-1", "port-1", Decimal("10000"), Decimal("1000"), {"AAPL": Decimal("9000")}, [], {}, datetime.now())
    with pytest.raises(DatabaseImmutabilityError):
        val.net_asset_value = Decimal("12000")

def test_valuation_and_exposure_calculation():
    exposure_service = ExposureCalculationService()
    asset_vals = {"AAPL": Decimal("4000"), "MSFT": Decimal("6000")}
    exps = exposure_service.calculate_exposures(asset_vals, Decimal("10000"))
    
    aapl_exp = next(e for e in exps if e.asset_id == "AAPL")
    msft_exp = next(e for e in exps if e.asset_id == "MSFT")
    
    assert aapl_exp.exposure_pct == Decimal("0.4")
    assert msft_exp.exposure_pct == Decimal("0.6")
    assert aapl_exp.exposure_value == Decimal("4000")

# 2. Repository Tests
def test_in_memory_repository_occ():
    repo = InMemoryPortfolioRepository()
    p = PortfolioAggregate("port-1", "owner-1")
    repo.save(p)
    
    # Save again with same version -> conflict
    with pytest.raises(ConcurrencyConflictError):
        repo.save(p)
        
    p.increment_version()
    repo.save(p) # Success

def test_file_repository_occ(tmp_path):
    repo = FilePortfolioRepository(base_dir=str(tmp_path))
    p = PortfolioAggregate("port-1", "owner-1")
    repo.save(p)
    
    with pytest.raises(ConcurrencyConflictError):
        repo.save(p)
        
    p.increment_version()
    repo.save(p)

def test_file_repository_immutability(tmp_path):
    repo = FileValuationRepository(base_dir=str(tmp_path))
    val = ValuationAggregate("val-1", "port-1", Decimal("1000"), Decimal("100"), {}, [], {}, datetime.now())
    repo.save(val)
    
    with pytest.raises(DatabaseImmutabilityError):
        repo.save(val)

def test_deterministic_replay_reconstruction():
    events_log = [
        {"portfolio_id": "port-1", "asset_id": "AAPL", "units": "10", "price": "150", "timestamp": "2026-06-14T10:00:00"},
        {"portfolio_id": "port-1", "asset_id": "AAPL", "units": "5", "price": "160", "timestamp": "2026-06-14T10:05:00"},
        {"portfolio_id": "port-1", "asset_id": "AAPL", "units": "-15", "price": "170", "timestamp": "2026-06-14T10:10:00"}
    ]
    
    # Replay logic to reconstruct state
    pos = PositionAggregate("pos-1", "port-1", "AAPL", Decimal("0"), Decimal("0"))
    for event in events_log:
        pos.update_position(Decimal(event["units"]), Decimal(event["price"]), "lot-1", datetime.fromisoformat(event["timestamp"]))
        
    assert pos.units == Decimal("0")
    assert pos.status == PositionStatus.CLOSED

# 3. Integration Tests
def test_order_filled_event_consumption():
    pos_repo = InMemoryPositionRepository()
    cash_repo = InMemoryCashLedgerRepository()
    val_repo = InMemoryValuationRepository()
    
    bench_svc = BenchmarkRegistryService()
    bench_svc.register_benchmark("SPY", Decimal("5000.0"))
    exp_svc = ExposureCalculationService()
    
    events = []
    val_svc = PortfolioValuationService(val_repo, exp_svc, bench_svc, events)
    proj_svc = PortfolioProjectionService(pos_repo, cash_repo, val_svc, events)
    
    # Initial Cash
    cash = CashLedgerAggregate("port-1", Decimal("10000"), Decimal("0"))
    cash_repo.save(cash)
    
    fill = {
        "portfolio_id": "port-1",
        "asset_id": "AAPL",
        "units": "10",
        "price": "150",
        "timestamp": datetime.utcnow().isoformat(),
        "event_id": "evt-1"
    }
    
    val = proj_svc.consume_order_filled(fill)
    
    assert val.net_asset_value == Decimal("10000") # Cash reduced by 1500, AAPL position worth 1500. NAV remains 10000.
    assert val.cash_balance == Decimal("8500")
    assert val.asset_valuations["AAPL"] == Decimal("1500")
    
    # Assert events emitted
    assert len([e for e in events if isinstance(e, HoldingsUpdatedEvent)]) == 1
    assert len([e for e in events if isinstance(e, CashUpdatedEvent)]) == 1
    assert len([e for e in events if isinstance(e, PositionOpenedEvent)]) == 1
    assert len([e for e in events if isinstance(e, PortfolioValuationCalculatedEvent)]) == 1

# 4. Architecture / Isolation Tests
def test_architecture_import_isolation():
    import sys
    for module in list(sys.modules.keys()):
        if module.startswith("karsa.portfolio"):
            filepath = sys.modules[module].__file__
            if filepath and filepath.endswith(".py"):
                with open(filepath, "r") as f:
                    content = f.read()
                assert "karsa.performance" not in content
                assert "karsa.risk" not in content
                assert "karsa.governance" not in content
