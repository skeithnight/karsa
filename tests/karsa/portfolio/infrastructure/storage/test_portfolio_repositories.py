import pytest
from testcontainers.postgres import PostgresContainer
from psycopg_pool import ConnectionPool

from karsa.portfolio.domain.model.portfolio import (
    Portfolio, Position, ExposureMetrics, PortfolioTargetSnapshot, TargetPosition
)
from karsa.portfolio.infrastructure.storage.in_memory_repositories import (
    InMemoryPortfolioRepository, InMemoryTargetSnapshotRepository
)
from karsa.portfolio.infrastructure.storage.postgres_repositories import (
    PostgresPortfolioRepository, PostgresTargetSnapshotRepository
)

@pytest.fixture(scope="module")
def postgres_pool():
    try:
        with PostgresContainer("postgres:15") as postgres:
            conn_str = postgres.get_connection_url().replace("postgresql+psycopg2", "postgresql")
            with ConnectionPool(conn_str) as pool:
                p_repo = PostgresPortfolioRepository(pool)
                t_repo = PostgresTargetSnapshotRepository(pool)
                p_repo._setup_schema()
                t_repo._setup_schema()
                yield pool
    except Exception as e:
        pytest.skip(f"Could not start Postgres container: {e}")

@pytest.fixture
def p_in_memory():
    return InMemoryPortfolioRepository()

@pytest.fixture
def t_in_memory():
    return InMemoryTargetSnapshotRepository()

@pytest.fixture
def p_postgres(postgres_pool):
    return PostgresPortfolioRepository(postgres_pool)

@pytest.fixture
def t_postgres(postgres_pool):
    return PostgresTargetSnapshotRepository(postgres_pool)

def _run_portfolio_repo_contract(repo):
    p = Portfolio("P-1")
    p.add_position(Position("POS-1", "P-1", "AAPL", 100, 150.0, 16000.0))
    p.update_exposure_metrics(ExposureMetrics(1.5, 0.8, 0.2, 0.1, 1.5))
    
    # Save & Get
    repo.save(p)
    loaded = repo.get_by_id("P-1")
    assert loaded is not None
    assert loaded.portfolio_id == "P-1"
    assert len(loaded.positions) == 1
    
    # Exists
    assert repo.exists("P-1") is True
    assert repo.exists("NON") is False
    
    # Update
    loaded.activate()
    repo.save(loaded)
    updated = repo.get_by_id("P-1")
    assert updated.state.value == "ACTIVE"
    
    # Delete
    repo.delete("P-1")
    assert repo.exists("P-1") is False

def _run_target_snapshot_repo_contract(repo):
    targets = frozenset([TargetPosition("AAPL", 0.8)])
    s = PortfolioTargetSnapshot("SNAP-1", "P-1", 1, targets)
    
    # Save & Get
    repo.save(s)
    loaded = repo.get_by_id("SNAP-1")
    assert loaded is not None
    assert loaded.snapshot_id == "SNAP-1"
    assert len(loaded.target_positions) == 1
    
    # Exists
    assert repo.exists("SNAP-1") is True
    
    # Delete
    repo.delete("SNAP-1")
    assert repo.exists("SNAP-1") is False

def test_in_memory_portfolio_repo(p_in_memory):
    _run_portfolio_repo_contract(p_in_memory)

def test_in_memory_target_snapshot_repo(t_in_memory):
    _run_target_snapshot_repo_contract(t_in_memory)

def test_postgres_portfolio_repo(p_postgres):
    _run_portfolio_repo_contract(p_postgres)

def test_postgres_target_snapshot_repo(t_postgres):
    _run_target_snapshot_repo_contract(t_postgres)
