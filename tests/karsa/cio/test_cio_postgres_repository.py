import pytest
from datetime import datetime, timezone, timedelta
from testcontainers.postgres import PostgresContainer
from psycopg_pool import ConnectionPool
import psycopg
import json

from karsa.cio.exceptions import ImmutabilityViolationException, DuplicateJournalRefException
from karsa.cio.value_objects import CommitteeVote, OverrideReason
from karsa.cio.models import CIODecisionAggregate
from karsa.cio.projections import PortfolioStateProjection
from karsa.cio.repositories import PostgresCIODecisionRepository

@pytest.fixture(scope="module")
def postgres_pool():
    local_conn_str = "postgresql://chaos:chaos@localhost:5432/chaos"
    try:
        with psycopg.connect(local_conn_str) as conn:
            pass
        with ConnectionPool(local_conn_str) as pool:
            yield pool
            return
    except Exception:
        pass

    try:
        with PostgresContainer("postgres:15") as postgres:
            conn_str = postgres.get_connection_url().replace("postgresql+psycopg2", "postgresql")
            with ConnectionPool(conn_str) as pool:
                yield pool
    except Exception as e:
        pytest.skip(f"Could not connect to local Postgres or start Postgres container: {e}")

@pytest.fixture
def clean_db(postgres_pool):
    with postgres_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS portfolio_states_default CASCADE;")
            cur.execute("DROP TABLE IF EXISTS portfolio_states CASCADE;")
            cur.execute("DROP TABLE IF EXISTS cio_decisions_default CASCADE;")
            cur.execute("DROP TABLE IF EXISTS cio_decisions CASCADE;")
            cur.execute("DROP TABLE IF EXISTS decision_journals CASCADE;")

            # 1. Create decision_journals table (for adapter checks)
            cur.execute("""
                CREATE TABLE decision_journals (
                    decision_id VARCHAR(128) PRIMARY KEY,
                    created_at TIMESTAMP NOT NULL
                );
            """)

            # 2. Recreate CIO schema exactly like Alembic migration does
            cur.execute("""
                CREATE TABLE cio_decisions (
                    decision_id VARCHAR(128) NOT NULL,
                    calculation_id VARCHAR(128),
                    governance_exception_id VARCHAR(128),
                    decision_journal_ref VARCHAR(128) NOT NULL,
                    portfolio_snapshot_hash VARCHAR(64) NOT NULL,
                    action_type VARCHAR(128) NOT NULL,
                    target_node_type VARCHAR(128) NOT NULL,
                    target_node_id VARCHAR(128) NOT NULL,
                    decision_payload JSONB NOT NULL DEFAULT '{}',
                    cryptographic_signature VARCHAR(256) NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (decision_id, created_at)
                ) PARTITION BY RANGE (created_at);

                CREATE TABLE cio_decisions_default PARTITION OF cio_decisions DEFAULT;

                CREATE TABLE portfolio_states (
                    state_id VARCHAR(128) NOT NULL,
                    decision_id VARCHAR(128) NOT NULL,
                    portfolio_tree JSONB NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (state_id, created_at)
                ) PARTITION BY RANGE (created_at);

                CREATE TABLE portfolio_states_default PARTITION OF portfolio_states DEFAULT;
            """)

            # 3. Recreate check_unique_decision_journal_ref trigger function
            cur.execute("""
                CREATE OR REPLACE FUNCTION check_unique_decision_journal_ref()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM cio_decisions
                        WHERE decision_journal_ref = NEW.decision_journal_ref
                    ) THEN
                        RAISE EXCEPTION 'decision_journal_ref already authorizes a CIO decision. 1:1 cardinality constraint violated.';
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER enforce_unique_decision_journal_ref
                BEFORE INSERT ON cio_decisions
                FOR EACH ROW EXECUTE FUNCTION check_unique_decision_journal_ref();
            """)

            # 4. Recreate block_cio_mutation trigger function
            cur.execute("""
                CREATE OR REPLACE FUNCTION block_cio_mutation()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'CIO records are strictly immutable. UPDATE and DELETE operations are prohibited.';
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER enforce_cio_decisions_immutability
                BEFORE UPDATE OR DELETE ON cio_decisions
                FOR EACH ROW EXECUTE FUNCTION block_cio_mutation();

                CREATE TRIGGER enforce_portfolio_states_immutability
                BEFORE UPDATE OR DELETE ON portfolio_states
                FOR EACH ROW EXECUTE FUNCTION block_cio_mutation();
            """)
        conn.commit()
    return postgres_pool

def test_postgres_save_and_retrieve(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresCIODecisionRepository(conn)
        
        now = datetime.utcnow().replace(microsecond=0)
        decision = CIODecisionAggregate(
            decision_id="dec-1",
            calculation_id="calc-1",
            governance_exception_id="exception-1",
            decision_journal_ref="urn:journal:dec-1",
            portfolio_snapshot_hash="hash-123",
            action_type="APPROVE_ALLOCATION",
            target_node_type="PORTFOLIO",
            target_node_id="port-1",
            decision_payload={"allocated_weights": {"worker-1": 1.0}},
            cryptographic_signature="sig-xyz",
            created_at=now,
            votes=[CommitteeVote("voter-1", "APPROVE", now)],
            override_reason=None
        )

        # Save to DB
        repo.save_decision(decision)
        conn.commit()

        # Retrieve and verify
        retrieved = repo.get_decision_by_id("dec-1")
        assert retrieved is not None
        assert retrieved.decision_id == "dec-1"
        assert retrieved.calculation_id == "calc-1"
        assert retrieved.governance_exception_id == "exception-1"
        assert retrieved.decision_journal_ref == "urn:journal:dec-1"
        assert retrieved.portfolio_snapshot_hash == "hash-123"
        assert retrieved.action_type == "APPROVE_ALLOCATION"
        assert retrieved.target_node_id == "port-1"
        assert len(retrieved.votes) == 1
        assert retrieved.votes[0].voter_id == "voter-1"
        assert retrieved.votes[0].vote_type == "APPROVE"

def test_postgres_enforces_1to1_cardinality(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresCIODecisionRepository(conn)
        now = datetime.utcnow().replace(microsecond=0)
        
        decision1 = CIODecisionAggregate(
            decision_id="dec-1",
            calculation_id="calc-1",
            governance_exception_id=None,
            decision_journal_ref="urn:journal:dec-duplicate",
            portfolio_snapshot_hash="hash-123",
            action_type="APPROVE_ALLOCATION",
            target_node_type="PORTFOLIO",
            target_node_id="port-1",
            decision_payload={"allocated_weights": {"worker-1": 1.0}},
            cryptographic_signature="sig-xyz",
            created_at=now,
            votes=[CommitteeVote("voter-1", "APPROVE", now)]
        )
        decision2 = CIODecisionAggregate(
            decision_id="dec-2",
            calculation_id="calc-2",
            governance_exception_id=None,
            decision_journal_ref="urn:journal:dec-duplicate",  # Same ref!
            portfolio_snapshot_hash="hash-123",
            action_type="APPROVE_ALLOCATION",
            target_node_type="PORTFOLIO",
            target_node_id="port-1",
            decision_payload={"allocated_weights": {"worker-1": 1.0}},
            cryptographic_signature="sig-xyz2",
            created_at=now + timedelta(seconds=1),
            votes=[CommitteeVote("voter-1", "APPROVE", now)]
        )

        repo.save_decision(decision1)
        conn.commit()

        # Saving second decision with same journal ref must fail with DuplicateJournalRefException
        with pytest.raises(DuplicateJournalRefException):
            repo.save_decision(decision2)
            conn.commit()

def test_postgres_enforces_immutability(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresCIODecisionRepository(conn)
        now = datetime.utcnow().replace(microsecond=0)
        
        decision = CIODecisionAggregate(
            decision_id="dec-1",
            calculation_id=None,
            governance_exception_id=None,
            decision_journal_ref="urn:journal:dec-1",
            portfolio_snapshot_hash="hash-123",
            action_type="APPROVE_ALLOCATION",
            target_node_type="PORTFOLIO",
            target_node_id="port-1",
            decision_payload={"allocated_weights": {"worker-1": 1.0}},
            cryptographic_signature="sig-xyz",
            created_at=now,
            votes=[CommitteeVote("voter-1", "APPROVE", now)]
        )

        repo.save_decision(decision)
        conn.commit()

        # Direct SQL UPDATE should trigger database exception
        with pytest.raises(psycopg.Error):
            with conn.cursor() as cur:
                cur.execute("UPDATE cio_decisions SET action_type = 'OVERRIDE' WHERE decision_id = 'dec-1'")
            conn.commit()

        # Direct SQL DELETE should also trigger database exception
        with pytest.raises(psycopg.Error):
            with conn.cursor() as cur:
                cur.execute("DELETE FROM cio_decisions WHERE decision_id = 'dec-1'")
            conn.commit()

def test_postgres_save_and_retrieve_portfolio_projection(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresCIODecisionRepository(conn)
        now = datetime.utcnow().replace(microsecond=0)

        # Save portfolio state projection
        projection = PortfolioStateProjection(
            state_id="state-1",
            decision_id="dec-1",
            portfolio_tree={"root": {"weights": {"worker-1": 1.0}}},
            created_at=now
        )
        repo.save_portfolio_state(projection)
        conn.commit()

        # Retrieve and verify
        retrieved = repo.get_latest_portfolio_state()
        assert retrieved is not None
        assert retrieved.state_id == "state-1"
        assert retrieved.portfolio_tree == {"root": {"weights": {"worker-1": 1.0}}}

        # Verify UPDATE on projection is blocked
        with pytest.raises(psycopg.Error):
            with conn.cursor() as cur:
                cur.execute("UPDATE portfolio_states SET decision_id = 'dec-2' WHERE state_id = 'state-1'")
            conn.commit()
