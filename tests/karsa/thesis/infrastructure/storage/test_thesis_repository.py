import pytest
from datetime import datetime, timezone
from testcontainers.postgres import PostgresContainer
from psycopg_pool import ConnectionPool

from karsa.thesis.domain.model.thesis import (
    ActiveThesis,
    ThesisVersion,
    ThesisReview,
    ThesisInvalidationRule,
    ThesisDependencyGraph,
    ThesisDependencyEdge,
    ThesisState
)
from karsa.thesis.infrastructure.storage.in_memory_thesis_repository import InMemoryThesisRepository
from karsa.thesis.infrastructure.storage.postgres_thesis_repository import PostgresThesisRepository

@pytest.fixture(scope="module")
def postgres_pool():
    try:
        with PostgresContainer("postgres:15") as postgres:
            conn_str = postgres.get_connection_url().replace("postgresql+psycopg2", "postgresql")
            with ConnectionPool(conn_str) as pool:
                repo = PostgresThesisRepository(pool)
                repo._setup_schema()
                yield pool
    except Exception as e:
        pytest.skip(f"Could not start Postgres container: {e}")

@pytest.fixture
def in_memory_repo():
    return InMemoryThesisRepository()

@pytest.fixture
def postgres_repo(postgres_pool):
    return PostgresThesisRepository(postgres_pool)

def _run_repository_contract_tests(repo):
    # 1. Save & Load thesis
    thesis = ActiveThesis("T-1", "author1", datetime.now(timezone.utc))
    repo.save(thesis)
    
    loaded = repo.get_by_id("T-1")
    assert loaded is not None
    assert loaded.thesis_id == "T-1"
    assert loaded.author == "author1"
    
    # 3. Update thesis
    loaded.degrade()
    repo.save(loaded)
    
    updated = repo.get_by_id("T-1")
    assert updated.state == ThesisState.DEGRADED
    
    # 5, 6, 7. Persist versions, reviews, graph
    updated.versions.append(ThesisVersion("v1", None, datetime.now(timezone.utc), "hash1"))
    updated.reviews.append(ThesisReview("r1", "rev1", datetime.now(timezone.utc), "APPROVE", "notes"))
    updated.invalidation_rules.append(ThesisInvalidationRule("rule1", "metric1", 10.0, ">", True))
    
    graph = ThesisDependencyGraph("g1")
    graph.add_edge(ThesisDependencyEdge("T-2", 0.5, "dep"))
    updated.dependency_graph = graph
    
    repo.save(updated)
    
    # 8. Load aggregate reconstruction
    fully_loaded = repo.get_by_id("T-1")
    assert len(fully_loaded.versions) == 1
    assert len(fully_loaded.reviews) == 1
    assert len(fully_loaded.invalidation_rules) == 1
    assert fully_loaded.dependency_graph is not None
    assert len(fully_loaded.dependency_graph.edges) == 1
    
    # 9. Repository existence checks
    assert repo.exists("T-1") is True
    assert repo.exists("T-999") is False
    
    # 4. Delete thesis
    repo.delete("T-1")
    assert repo.get_by_id("T-1") is None
    assert repo.exists("T-1") is False

def test_in_memory_repository_contract(in_memory_repo):
    _run_repository_contract_tests(in_memory_repo)

def test_postgres_repository_contract(postgres_repo):
    _run_repository_contract_tests(postgres_repo)

def test_postgres_multiple_save_update(postgres_repo):
    thesis = ActiveThesis("T-2", "author2", datetime.now(timezone.utc))
    postgres_repo.save(thesis)
    
    thesis.degrade()
    postgres_repo.save(thesis)
    
    thesis.request_review()
    postgres_repo.save(thesis)
    
    loaded = postgres_repo.get_by_id("T-2")
    assert loaded.state == ThesisState.UNDER_REVIEW
