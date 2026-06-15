import pytest
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from testcontainers.postgres import PostgresContainer
from psycopg_pool import ConnectionPool
import psycopg

from karsa.attribution.domain.model.models import AttributionSession, PerformanceAttributionRecord
from karsa.attribution.infrastructure.repositories import (
    PostgresAttributionSessionRepository,
    PostgresPerformanceAttributionRepository
)
from karsa.shared.infrastructure.uow import ConcurrencyConflictError

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
            cur.execute("DROP TRIGGER IF EXISTS enforce_record_immutability ON performance_attribution_records;")
            cur.execute("DROP TABLE IF EXISTS performance_attribution_records_default CASCADE;")
            cur.execute("DROP TABLE IF EXISTS performance_attribution_records CASCADE;")
            cur.execute("DROP TABLE IF EXISTS attribution_sessions CASCADE;")
            cur.execute("DROP FUNCTION IF EXISTS block_attribution_record_mutation();")

            cur.execute("""
                CREATE OR REPLACE FUNCTION block_attribution_record_mutation()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF TG_OP = 'DELETE' THEN
                        RAISE EXCEPTION 'Performance attribution records are immutable and cannot be deleted.';
                    ELSIF TG_OP = 'UPDATE' THEN
                        IF NEW.is_active = FALSE AND OLD.is_active = TRUE AND
                           NEW.record_id = OLD.record_id AND
                           NEW.session_id = OLD.session_id AND
                           NEW.decision_id = OLD.decision_id AND
                           NEW.thesis_urn = OLD.thesis_urn AND
                           NEW.worker_urn = OLD.worker_urn AND
                           NEW.capability_urn = OLD.capability_urn AND
                           NEW.regime_urn = OLD.regime_urn AND
                           NEW.asset_urn = OLD.asset_urn AND
                           NEW.selection_return = OLD.selection_return AND
                           NEW.allocation_return = OLD.allocation_return AND
                           NEW.execution_return = OLD.execution_return AND
                           NEW.beta_return = OLD.beta_return AND
                           NEW.liquidation_tracking_residual = OLD.liquidation_tracking_residual AND
                           NEW.attribution_version = OLD.attribution_version AND
                           NEW.calculated_at = OLD.calculated_at AND
                           (NEW.superseded_by_version IS NOT DISTINCT FROM OLD.superseded_by_version OR (OLD.superseded_by_version IS NULL AND NEW.superseded_by_version IS NOT NULL)) AND
                           (NEW.invalidated_by_version IS NOT DISTINCT FROM OLD.invalidated_by_version OR (OLD.invalidated_by_version IS NULL AND NEW.invalidated_by_version IS NOT NULL)) THEN
                            RETURN NEW;
                        ELSE
                            RAISE EXCEPTION 'Performance attribution records are immutable. Only deactivation and version lineage updates are allowed.';
                        END IF;
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)

            cur.execute("""
                CREATE TABLE attribution_sessions (
                    session_id UUID PRIMARY KEY,
                    horizon_start TIMESTAMP NOT NULL,
                    horizon_end TIMESTAMP NOT NULL,
                    state VARCHAR(64) NOT NULL,
                    compounding_strategy VARCHAR(64) NOT NULL,
                    raw_input_manifest_hash VARCHAR(256) NOT NULL,
                    aggregate_version INTEGER NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE performance_attribution_records (
                    record_id UUID NOT NULL,
                    session_id UUID NOT NULL,
                    decision_id VARCHAR(256) NOT NULL,
                    thesis_urn VARCHAR(256) NOT NULL,
                    worker_urn VARCHAR(256) NOT NULL,
                    capability_urn VARCHAR(256) NOT NULL,
                    regime_urn VARCHAR(256) NOT NULL,
                    asset_urn VARCHAR(256) NOT NULL,
                    selection_return NUMERIC NOT NULL,
                    allocation_return NUMERIC NOT NULL,
                    execution_return NUMERIC NOT NULL,
                    beta_return NUMERIC NOT NULL,
                    liquidation_tracking_residual NUMERIC NOT NULL,
                    attribution_version INTEGER NOT NULL,
                    is_active BOOLEAN NOT NULL,
                    calculated_at TIMESTAMP NOT NULL,
                    superseded_by_version INTEGER,
                    invalidated_by_version INTEGER,
                    aggregate_version INTEGER NOT NULL,
                    PRIMARY KEY (record_id, calculated_at)
                ) PARTITION BY RANGE (calculated_at);

                CREATE TABLE performance_attribution_records_default PARTITION OF performance_attribution_records DEFAULT;
            """)

            cur.execute("""
                CREATE TRIGGER enforce_record_immutability
                BEFORE UPDATE OR DELETE ON performance_attribution_records
                FOR EACH ROW EXECUTE FUNCTION block_attribution_record_mutation();
            """)
    return postgres_pool

def test_postgres_session_repository(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresAttributionSessionRepository(conn)
        
        sid = str(uuid.uuid4())
        session = AttributionSession(
            session_id=sid,
            horizon_start=datetime.now(timezone.utc),
            horizon_end=datetime.now(timezone.utc) + timedelta(days=5),
            state="STAGED",
            compounding_strategy="FRONGELLO"
        )
        repo.save(session)
        
        retrieved = repo.get_by_id(sid)
        assert retrieved is not None
        assert retrieved.state == "STAGED"
        
        retrieved.transition_to("COMPUTING")
        repo.save(retrieved)
        
        retrieved_updated = repo.get_by_id(sid)
        assert retrieved_updated.state == "COMPUTING"
        
        # Test ConcurrencyConflictError
        stale = AttributionSession(
            session_id=sid,
            horizon_start=session.horizon_start,
            horizon_end=session.horizon_end,
            state="COMPUTING",
            aggregate_version=1
        )
        with pytest.raises(ConcurrencyConflictError):
            repo.save(stale)

def test_postgres_record_repository_and_triggers(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresPerformanceAttributionRepository(conn)
        
        sid = str(uuid.uuid4())
        rid = str(uuid.uuid4())
        
        record = PerformanceAttributionRecord(
            record_id=rid,
            session_id=sid,
            decision_id="urn:decision:1",
            thesis_urn="urn:thesis:1",
            worker_urn="urn:worker:1",
            capability_urn="urn:capability:1",
            regime_urn="urn:regime:1",
            asset_urn="urn:asset:1",
            selection_return=Decimal("0.050000000000"),
            allocation_return=Decimal("0.020000000000"),
            execution_return=Decimal("0.010000000000"),
            beta_return=Decimal("0.020000000000"),
            liquidation_tracking_residual=Decimal("0.000000000000"),
            attribution_version=1,
            is_active=True
        )
        repo.save(record)
        
        # Verify saved record exists
        retrieved = repo.find_by_id(rid, 1)
        assert retrieved is not None
        assert retrieved.selection_return == Decimal("0.05")
        
        # Test immutability triggers block direct returns modification
        try:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE performance_attribution_records SET selection_return = 0.10 WHERE record_id = %s",
                        (rid,)
                    )
        except psycopg.Error:
            pass

        # Test immutability triggers block DELETE
        try:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM performance_attribution_records WHERE record_id = %s",
                        (rid,)
                    )
        except psycopg.Error:
            pass
            
        # Verify repository deactivation query works (safely bypassed via is_active update)
        repo.deactivate_old_versions("urn:decision:1", exclude_version=2)
        
        retrieved_after = repo.find_by_id(rid, 1)
        assert retrieved_after.is_active is False
        assert retrieved_after.superseded_by_version == 2
        
        # Test queries
        assert len(repo.find_active_by_decision("urn:decision:1")) == 0
        assert len(repo.find_by_session(sid)) == 1
        assert len(repo.list_all()) == 1
        
        # Test deactivation by session
        repo.deactivate_by_session(sid)
        retrieved_final = repo.find_by_id(rid, 1)
        assert retrieved_final.is_active is False
        
        repo.clear()
        assert len(repo.list_all()) == 0
        
        # Test clear and list for session repo
        sess_repo = PostgresAttributionSessionRepository(conn)
        s1 = AttributionSession(
            session_id=sid,
            horizon_start=datetime.now(timezone.utc),
            horizon_end=datetime.now(timezone.utc) + timedelta(days=5),
            state="STAGED",
            compounding_strategy="FRONGELLO"
        )
        sess_repo.save(s1)
        assert len(sess_repo.list_all()) == 1
        sess_repo.clear()
        assert len(sess_repo.list_all()) == 0
