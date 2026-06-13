import pytest
import json
from unittest.mock import MagicMock

from karsa.allocation.domain.model.allocation import RiskAllocation, RiskBudget, LiquidityConstraint
from karsa.portfolio.domain.model.portfolio import Portfolio, RegimeState, AllocationPortfolioMapping
from karsa.portfolio.domain.service.rebalancing_engine import RebalancingEngine
from karsa.portfolio.infrastructure.storage.in_memory_repositories import InMemoryPortfolioRepository
from karsa.portfolio.application.service.portfolio_application_service import PortfolioApplicationService
from karsa.portfolio.application.port.treasury_port import TreasuryPort
from karsa.portfolio.application.port.regime_port import RegimePort
from karsa.portfolio.application.port.allocation_port import AllocationPort
from karsa.shared.infrastructure.uow import UnitOfWork

class MockTreasuryPort(TreasuryPort):
    def get_buying_power(self, portfolio_id: str) -> float:
        return 100000.0

class MockRegimePort(RegimePort):
    def get_current_regime(self) -> RegimeState:
        return RegimeState("BULL", "LOW", "HIGH", 0.9)

class MockAllocationPort(AllocationPort):
    def __init__(self):
        self.allocations = []
        self.mappings = []

    def get_allocations_for_portfolio(self, portfolio_id: str):
        return self.allocations

    def get_mappings_for_portfolio(self, portfolio_id: str):
        return self.mappings

class MockOutboxRepository:
    def __init__(self):
        self.records = []
    
    def save(self, record):
        self.records.append(record)

class MockUnitOfWork(UnitOfWork):
    def __init__(self):
        self.outbox_repository = MockOutboxRepository()

    def start(self):
        pass
        
    def commit(self):
        pass
        
    def rollback(self):
        pass

@pytest.fixture
def service_deps():
    p_repo = InMemoryPortfolioRepository()
    t_port = MockTreasuryPort()
    r_port = MockRegimePort()
    a_port = MockAllocationPort()
    uow = MockUnitOfWork()
    engine = RebalancingEngine()
    
    svc = PortfolioApplicationService(
        portfolio_repo=p_repo,
        treasury_port=t_port,
        regime_port=r_port,
        allocation_port=a_port,
        rebalancing_engine=engine,
        uow=uow
    )
    
    return svc, p_repo, a_port, uow

def test_missing_portfolio(service_deps):
    svc = service_deps[0]
    with pytest.raises(ValueError, match="Portfolio P-1 not found"):
        svc.propose_rebalance("P-1")

def test_missing_allocations(service_deps):
    svc, p_repo, *_ = service_deps
    p_repo.save(Portfolio("P-1"))
    with pytest.raises(ValueError, match="No active allocations found"):
        svc.propose_rebalance("P-1")

def test_successful_propose_workflow(service_deps):
    svc, p_repo, a_port, uow = service_deps
    
    # Setup
    p_repo.save(Portfolio("P-1"))
    budget = RiskBudget(0.1, 0.1, LiquidityConstraint(0.1, 5.0))
    a_port.allocations = [RiskAllocation("A-1", "T-1", budget)]
    a_port.mappings = [AllocationPortfolioMapping("A-1", "P-1", 1.0)]
    
    # Execute
    svc.propose_rebalance("P-1")
    
    # Assert Outbox received PortfolioDecisionProposed
    assert len(uow.outbox_repository.records) == 1
    record = uow.outbox_repository.records[0]
    payload = json.loads(record.payload)
    
    assert payload["event_type"] == "PortfolioDecisionProposed"
    assert payload["aggregate_type"] == "Portfolio"
    assert payload["aggregate_id"] == "P-1"
    
    event_payload = payload["payload"]
    assert "decision_id" in event_payload["decision_payload"]
    assert "target_snapshot_id" in event_payload["decision_payload"]
    assert "originator_id" in event_payload["originator_identity"]

def test_apply_approved_decision(service_deps):
    svc, p_repo, a_port, uow = service_deps
    
    # Setup
    p_repo.save(Portfolio("P-1"))
    
    # Execute apply
    svc.apply_approved_decision("P-1", "S-1", "corr-1", "cause-1")
    
    # Assert Portfolio was updated
    p_updated = p_repo.get_by_id("P-1")
    assert p_updated.current_target_snapshot_id == "S-1"
    assert p_updated.aggregate_version == 1
    
    # Assert Outbox received PortfolioTargetUpdated
    assert len(uow.outbox_repository.records) == 1
    record = uow.outbox_repository.records[0]
    payload = json.loads(record.payload)
    
    assert payload["event_type"] == "PortfolioTargetUpdated"
    assert payload["correlation_id"] == "corr-1"
    assert payload["causation_id"] == "cause-1"
    
    event_payload = payload["payload"]
    assert event_payload["portfolio_id"] == "P-1"
    assert event_payload["target_snapshot_id"] == "S-1"

