import pytest
from datetime import datetime, timezone
from testcontainers.postgres import PostgresContainer
from psycopg_pool import ConnectionPool
import psycopg
import json
import uuid

from karsa.post_mortem.exceptions import (
    ImmutabilityViolationException,
    RecommendationStateConflictException,
)
from karsa.post_mortem.value_objects import (
    IncidentReference,
    FailureClassification,
    RootCauseContribution,
    PostMortemFinding,
)
from karsa.post_mortem.models import PostMortemRecord, Recommendation
from karsa.post_mortem.repositories import (
    PostgresPostMortemRecordRepository,
    PostgresRecommendationRepository,
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
            # Drop tables in correct order
            cur.execute("DROP TABLE IF EXISTS recommendation_state_history CASCADE;")
            cur.execute("DROP TABLE IF EXISTS post_mortem_recommendations CASCADE;")
            cur.execute("DROP TABLE IF EXISTS post_mortem_records_default CASCADE;")
            cur.execute("DROP TABLE IF EXISTS post_mortem_records CASCADE;")

            # 1. Create post_mortem_records table (partitioned by range on created_at)
            cur.execute("""
                CREATE TABLE post_mortem_records (
                    postmortem_id VARCHAR(128) NOT NULL,
                    incident_ref VARCHAR(128) NOT NULL,
                    failure_classification JSONB NOT NULL,
                    root_causes JSONB NOT NULL,
                    findings JSONB NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (postmortem_id, created_at)
                ) PARTITION BY RANGE (created_at);

                CREATE TABLE post_mortem_records_default PARTITION OF post_mortem_records DEFAULT;
            """)

            # 2. Create post_mortem_recommendations table (OCC protected with version)
            cur.execute("""
                CREATE TABLE post_mortem_recommendations (
                    recommendation_id VARCHAR(128) PRIMARY KEY,
                    postmortem_id VARCHAR(128) NOT NULL,
                    target_context VARCHAR(64) NOT NULL,
                    action_item TEXT NOT NULL,
                    parameters JSONB NOT NULL,
                    state VARCHAR(32) NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    updated_at TIMESTAMP NOT NULL
                );
            """)

            # 3. Create recommendation_state_history table
            cur.execute("""
                CREATE TABLE recommendation_state_history (
                    history_id VARCHAR(128) PRIMARY KEY,
                    recommendation_id VARCHAR(128) NOT NULL,
                    from_state VARCHAR(32) NOT NULL,
                    to_state VARCHAR(32) NOT NULL,
                    version INTEGER NOT NULL,
                    transitioned_at TIMESTAMP NOT NULL
                );
            """)

            # 4. Recreate check_unique_incident_ref trigger function to enforce 1:1 cardinality on partitioned table
            cur.execute("""
                CREATE OR REPLACE FUNCTION check_unique_incident_ref()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM post_mortem_records
                        WHERE incident_ref = NEW.incident_ref
                    ) THEN
                        RAISE EXCEPTION 'incident_ref already has a post-mortem record. 1:1 cardinality constraint violated.';
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER enforce_unique_incident_ref
                BEFORE INSERT ON post_mortem_records
                FOR EACH ROW EXECUTE FUNCTION check_unique_incident_ref();
            """)

            # 5. Recreate block UPDATE/DELETE trigger for post_mortem_records
            cur.execute("""
                CREATE OR REPLACE FUNCTION block_post_mortem_record_mutation()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'Post-mortem records are strictly immutable. UPDATE and DELETE operations are prohibited.';
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER enforce_post_mortem_records_immutability
                BEFORE UPDATE OR DELETE ON post_mortem_records
                FOR EACH ROW EXECUTE FUNCTION block_post_mortem_record_mutation();
            """)
        conn.commit()
    return postgres_pool

def test_postgres_save_and_retrieve_record(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresPostMortemRecordRepository(conn)
        now = datetime.utcnow().replace(microsecond=0)
        
        fc = FailureClassification("THESIS_FAILURE", "HIGH")
        rc = RootCauseContribution("PARAMETER_OVERFITTING", 1.0, "Overfitting")
        findings = PostMortemFinding(timeline_events=[], evidence_uris=[])
        
        record = PostMortemRecord(
            postmortem_id="pm-1",
            incident_ref=IncidentReference("urn:karsa:incident:thesis:100"),
            failure_classification=fc,
            root_causes=[rc],
            findings=findings,
            created_at=now
        )
        
        # Save record
        repo.save_record(record)
        conn.commit()

        # Retrieve and assert
        retrieved = repo.get_record_by_id("pm-1")
        assert retrieved is not None
        assert retrieved.postmortem_id == "pm-1"
        assert retrieved.incident_ref.incident_ref == "urn:karsa:incident:thesis:100"
        assert retrieved.failure_classification.failure_type == "THESIS_FAILURE"
        assert retrieved.root_causes[0].cause_category == "PARAMETER_OVERFITTING"
        assert retrieved.root_causes[0].weight == 1.0
        assert retrieved.created_at == now

        # Get by incident ref
        retrieved_by_ref = repo.get_record_by_incident_ref("urn:karsa:incident:thesis:100")
        assert retrieved_by_ref is not None
        assert retrieved_by_ref.postmortem_id == "pm-1"

def test_postgres_trigger_blocks_update(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresPostMortemRecordRepository(conn)
        now = datetime.utcnow().replace(microsecond=0)
        
        fc = FailureClassification("THESIS_FAILURE", "HIGH")
        rc = RootCauseContribution("PARAMETER_OVERFITTING", 1.0, "Overfitting")
        findings = PostMortemFinding([], [])
        
        record = PostMortemRecord(
            postmortem_id="pm-1",
            incident_ref=IncidentReference("urn:karsa:incident:thesis:101"),
            failure_classification=fc,
            root_causes=[rc],
            findings=findings,
            created_at=now
        )
        
        repo.save_record(record)
        conn.commit()

        # Try updating the record
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.RaiseException) as exc:
                cur.execute(
                    "UPDATE post_mortem_records SET incident_ref = 'new_ref' WHERE postmortem_id = 'pm-1'"
                )
            assert "UPDATE and DELETE operations are prohibited" in str(exc.value)

def test_postgres_trigger_blocks_delete(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresPostMortemRecordRepository(conn)
        now = datetime.utcnow().replace(microsecond=0)
        
        fc = FailureClassification("THESIS_FAILURE", "HIGH")
        rc = RootCauseContribution("PARAMETER_OVERFITTING", 1.0, "Overfitting")
        findings = PostMortemFinding([], [])
        
        record = PostMortemRecord(
            postmortem_id="pm-1",
            incident_ref=IncidentReference("urn:karsa:incident:thesis:102"),
            failure_classification=fc,
            root_causes=[rc],
            findings=findings,
            created_at=now
        )
        
        repo.save_record(record)
        conn.commit()

        # Try deleting the record
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.RaiseException) as exc:
                cur.execute(
                    "DELETE FROM post_mortem_records WHERE postmortem_id = 'pm-1'"
                )
            assert "UPDATE and DELETE operations are prohibited" in str(exc.value)

def test_postgres_recommendation_concurrency_and_history(clean_db):
    with clean_db.connection() as conn:
        rec_repo = PostgresRecommendationRepository(conn)
        now = datetime.utcnow().replace(microsecond=0)

        # Create recommendation in PROPOSED state
        rec = Recommendation(
            recommendation_id="rec-1",
            postmortem_id="pm-1",
            target_context="GOVERNANCE",
            action_item="Reduce max leverage limit",
            parameters={"max_leverage": 1.5},
            state="PROPOSED",
            version=1,
            updated_at=now
        )

        rec_repo.save_recommendation(rec)
        conn.commit()

        # Verify it is stored
        retrieved = rec_repo.get_recommendation_by_id("rec-1")
        assert retrieved is not None
        assert retrieved.state == "PROPOSED"
        assert retrieved.version == 1

        # Verify history is populated
        with conn.cursor() as cur:
            cur.execute(
                "SELECT from_state, to_state, version FROM recommendation_state_history WHERE recommendation_id = 'rec-1'"
            )
            rows = cur.fetchall()
            assert len(rows) == 1
            assert rows[0] == ("None", "PROPOSED", 1)

        # Simulate concurrent writes
        rec_writer1 = rec_repo.get_recommendation_by_id("rec-1")
        rec_writer2 = rec_repo.get_recommendation_by_id("rec-1")

        # Writer 1 transitions to ACCEPTED
        rec_writer1.accept()
        rec_repo.save_recommendation(rec_writer1)
        conn.commit()

        # Writer 2 transitions to REJECTED from stale data (version 1)
        rec_writer2.reject()
        with pytest.raises(ConcurrencyConflictError):
            rec_repo.save_recommendation(rec_writer2)

        # Retrieve and check that Writer 1's transition succeeded and generated history
        final_rec = rec_repo.get_recommendation_by_id("rec-1")
        assert final_rec.state == "ACCEPTED"
        assert final_rec.version == 2

        with conn.cursor() as cur:
            cur.execute(
                "SELECT from_state, to_state, version FROM recommendation_state_history WHERE recommendation_id = 'rec-1' ORDER BY version ASC"
            )
            rows = cur.fetchall()
            assert len(rows) == 2
            assert rows[0] == ("None", "PROPOSED", 1)
            assert rows[1] == ("PROPOSED", "ACCEPTED", 2)
