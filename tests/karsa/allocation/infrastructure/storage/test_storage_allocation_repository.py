import pytest
from testcontainers.postgres import PostgresContainer
from psycopg_pool import ConnectionPool

from karsa.allocation.domain.model.allocation import (
    RiskAllocation, RiskBudget, LiquidityConstraint, AllocationState
)
from karsa.allocation.infrastructure.storage.in_memory_allocation_repository import InMemoryAllocationRepository
from karsa.allocation.infrastructure.storage.postgres_allocation_repository import PostgresAllocationRepository

@pytest.fixture(scope="module")
def postgres_pool():
    try:
        with PostgresContainer("postgres:15") as postgres:
            conn_str = postgres.get_connection_url().replace("postgresql+psycopg2", "postgresql")
            with ConnectionPool(conn_str) as pool:
                repo = PostgresAllocationRepository(pool)
                repo._setup_schema()
                yield pool
    except Exception as e:
        pytest.skip(f"Could not start Postgres container: {e}")

@pytest.fixture
def in_memory_repo():
    return InMemoryAllocationRepository()

@pytest.fixture
def postgres_repo(postgres_pool):
    return PostgresAllocationRepository(postgres_pool)

def _run_repository_contract_tests(repo):
    liquidity = LiquidityConstraint(max_adv_participation=0.1, max_days_to_liquidate=5.0)
    budget = RiskBudget(volatility_budget=0.15, drawdown_limit=0.10, liquidity_constraint=liquidity)
    allocation = RiskAllocation("A-1", "T-1", budget)
    
    # 1. Save and Load
    repo.save(allocation)
    loaded = repo.get_by_id("A-1")
    assert loaded is not None
    assert loaded.allocation_id == "A-1"
    assert loaded.thesis_id == "T-1"
    assert loaded.state == AllocationState.PENDING
    
    # 2. Update
    loaded.activate()
    loaded.scale_volatility_budget(0.30) # budget drops to 0.075
    repo.save(loaded)
    
    updated = repo.get_by_id("A-1")
    assert updated.state == AllocationState.ACTIVE
    assert updated.risk_budget.volatility_budget == pytest.approx(0.075)
    
    # 3. Exists
    assert repo.exists("A-1") is True
    assert repo.exists("NONEXISTENT") is False
    
    # 4. Delete
    repo.delete("A-1")
    assert repo.exists("A-1") is False
    assert repo.get_by_id("A-1") is None

def test_in_memory_repository_contract(in_memory_repo):
    _run_repository_contract_tests(in_memory_repo)

def test_postgres_repository_contract(postgres_repo):
    _run_repository_contract_tests(postgres_repo)
