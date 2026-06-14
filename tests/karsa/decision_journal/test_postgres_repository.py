import pytest
import hashlib
from datetime import datetime, timezone
from testcontainers.postgres import PostgresContainer
from psycopg_pool import ConnectionPool

from karsa.decision_journal.exceptions import ImmutabilityViolationException
from karsa.decision_journal.value_objects import (
    PromptReference, DatasetReference, TelemetryReference, ArtifactReference, ReplayMetadata, DecisionContextSnapshot, DecisionEvidence,
    DecisionRationale, DecisionHypothesis, DecisionConfidence
)
from karsa.decision_journal.models import DecisionJournalAggregate, DecisionRevisionAggregate, DecisionEvidenceAggregate
from karsa.decision_journal.projections import ActiveLeafProjection
from karsa.decision_journal.repositories import PostgresDecisionJournalRepository, PostgresActiveLeafProjectionRepository
from karsa.shared.infrastructure.uow import ConcurrencyConflictError

@pytest.fixture(scope="module")
def postgres_pool():
    import psycopg
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
            cur.execute("DROP TABLE IF EXISTS active_leaf_projections CASCADE;")
            cur.execute("DROP TABLE IF EXISTS decision_evidences CASCADE;")
            cur.execute("DROP TABLE IF EXISTS decision_revisions CASCADE;")
            cur.execute("DROP TABLE IF EXISTS decision_journals CASCADE;")
            
            # Recreate schema exactly like Alembic migration does
            cur.execute("""
                CREATE TABLE decision_journals (
                    decision_id VARCHAR(128) NOT NULL,
                    parent_decision_id VARCHAR(128),
                    root_decision_id VARCHAR(128) NOT NULL,
                    proposing_agent_id VARCHAR(128) NOT NULL,
                    signature VARCHAR(256) NOT NULL,
                    thesis_urn VARCHAR(128) NOT NULL,
                    context_hash VARCHAR(64) NOT NULL,
                    context_uri VARCHAR(512) NOT NULL,
                    context_snapshot_json JSONB NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (decision_id, root_decision_id, created_at)
                ) PARTITION BY RANGE (created_at);
                
                CREATE TABLE decision_revisions (
                    revision_id VARCHAR(128) NOT NULL,
                    parent_decision_id VARCHAR(128) NOT NULL,
                    root_decision_id VARCHAR(128) NOT NULL,
                    proposing_agent_id VARCHAR(128) NOT NULL,
                    signature VARCHAR(256) NOT NULL,
                    correction_reason VARCHAR(512) NOT NULL,
                    context_hash VARCHAR(64) NOT NULL,
                    context_uri VARCHAR(512) NOT NULL,
                    context_snapshot_json JSONB NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (revision_id, root_decision_id, created_at)
                ) PARTITION BY RANGE (created_at);

                CREATE TABLE decision_evidences (
                    evidence_id VARCHAR(128) NOT NULL,
                    decision_id VARCHAR(128) NOT NULL,
                    attached_by_agent_id VARCHAR(128) NOT NULL,
                    signature VARCHAR(256) NOT NULL,
                    evidence_json JSONB NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (evidence_id, created_at)
                ) PARTITION BY RANGE (created_at);

                CREATE TABLE active_leaf_projections (
                    root_decision_id VARCHAR(128) PRIMARY KEY,
                    active_leaf_decision_id VARCHAR(128) NOT NULL,
                    version INTEGER NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE OR REPLACE FUNCTION block_journal_mutation()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'Decision Journal records are strictly immutable. UPDATE and DELETE operations are prohibited.';
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER enforce_journal_immutability
                BEFORE UPDATE OR DELETE ON decision_journals
                FOR EACH ROW EXECUTE FUNCTION block_journal_mutation();

                CREATE TRIGGER enforce_revision_immutability
                BEFORE UPDATE OR DELETE ON decision_revisions
                FOR EACH ROW EXECUTE FUNCTION block_journal_mutation();

                CREATE TRIGGER enforce_evidence_immutability
                BEFORE UPDATE OR DELETE ON decision_evidences
                FOR EACH ROW EXECUTE FUNCTION block_journal_mutation();
            """)
        conn.commit()
    return postgres_pool

@pytest.fixture
def snapshot() -> DecisionContextSnapshot:
    prompt = PromptReference("pr-1", "hash-prompt", "urn:prompt:1")
    dataset = DatasetReference("ds-1", "hash-dataset", "urn:dataset:1")
    telemetry = TelemetryReference("tel-1", "hash-tel", "span-1")
    artifact = ArtifactReference("art-1", "hash-art", "urn:artifact:1")
    meta = ReplayMetadata("git-1", "docker-1", 42, 0.7, "high-vol", "hp", "hd", "ha")
    rationale = DecisionRationale("Verification Rationale", "Verification Assumptions")
    hypothesis = DecisionHypothesis("urn:thesis:verification", 150, 7200)
    confidence = DecisionConfidence(0.9, 0.05)
    return DecisionContextSnapshot(prompt, dataset, telemetry, artifact, meta, rationale, hypothesis, confidence)

def test_postgres_decision_journal_repository_flow(clean_db, snapshot):
    with clean_db.connection() as conn:
        repo = PostgresDecisionJournalRepository(conn)

        # 1. Test Save and Get Journal
        created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        journal = DecisionJournalAggregate(
            decision_id="dec-pg-1",
            proposing_agent_id="agt-1",
            signature="sig-1",
            thesis_urn="urn:thesis:1",
            context_snapshot=snapshot,
            created_at=created_at,
            context_hash="hash-context-1",
            context_uri="s3://contexts/dec-pg-1.json"
        )
        repo.save_journal(journal)

        loaded_journal = repo.get_journal_by_id("dec-pg-1")
        assert loaded_journal is not None
        assert loaded_journal.decision_id == "dec-pg-1"
        assert loaded_journal.proposing_agent_id == "agt-1"
        assert loaded_journal.signature == "sig-1"
        assert loaded_journal.thesis_urn == "urn:thesis:1"
        assert loaded_journal.context_hash == "hash-context-1"
        assert loaded_journal.context_uri == "s3://contexts/dec-pg-1.json"
        assert loaded_journal.context_snapshot.replay_metadata.prompt_hash == "hp"
        assert loaded_journal.rationale.reasoning_steps == "Verification Rationale"
        assert loaded_journal.hypothesis.expected_return_bps == 150
        assert loaded_journal.confidence.probability == 0.9

        # 2. Test Save and Get Revision
        revision = DecisionRevisionAggregate(
            revision_id="rev-pg-1",
            parent_decision_id="dec-pg-1",
            root_decision_id="dec-pg-1",
            proposing_agent_id="agt-1",
            signature="sig-2",
            correction_reason="Parameters tweaking",
            context_snapshot=snapshot,
            created_at=created_at,
            context_hash="hash-context-rev",
            context_uri="s3://contexts/rev-pg-1.json"
        )
        repo.save_revision(revision)

        loaded_rev = repo.get_revision_by_id("rev-pg-1")
        assert loaded_rev is not None
        assert loaded_rev.revision_id == "rev-pg-1"
        assert loaded_rev.parent_decision_id == "dec-pg-1"
        assert loaded_rev.root_decision_id == "dec-pg-1"
        assert loaded_rev.correction_reason == "Parameters tweaking"
        assert loaded_rev.rationale.reasoning_steps == "Verification Rationale"

        all_revisions = repo.get_all_revisions_by_root_id("dec-pg-1")
        assert len(all_revisions) == 1
        assert all_revisions[0].revision_id == "rev-pg-1"

        # 3. Test Save and Get Evidence
        evidence_val = DecisionEvidence(
            evidence_id="ev-1",
            description="execution trace",
            artifact_ref=ArtifactReference("art-2", "hash-art-2", "urn:artifact:2"),
            attached_at=created_at
        )
        evidence_agg = DecisionEvidenceAggregate(
            evidence_id="ev-agg-1",
            decision_id="dec-pg-1",
            attached_by_agent_id="agt-1",
            signature="sig-ev",
            evidence=evidence_val,
            created_at=created_at
        )
        repo.save_evidence(evidence_agg)

        evidences = repo.get_evidences_by_decision_id("dec-pg-1")
        assert len(evidences) == 1
        assert evidences[0].evidence_id == "ev-agg-1"
        assert evidences[0].evidence.description == "execution trace"

        conn.commit()

        # 4. Test Immutability Trigger (UPDATE/DELETE must fail)
        with pytest.raises(Exception) as excinfo:
            with conn.cursor() as cur:
                cur.execute("UPDATE decision_journals SET signature = 'tampered' WHERE decision_id = 'dec-pg-1';")
        assert "strictly immutable" in str(excinfo.value)
        conn.rollback()

        with pytest.raises(Exception) as excinfo:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM decision_journals WHERE decision_id = 'dec-pg-1';")
        assert "strictly immutable" in str(excinfo.value)
        conn.rollback()

        with pytest.raises(Exception) as excinfo:
            with conn.cursor() as cur:
                cur.execute("UPDATE decision_revisions SET correction_reason = 'tampered' WHERE revision_id = 'rev-pg-1';")
        assert "strictly immutable" in str(excinfo.value)
        conn.rollback()

        with pytest.raises(Exception) as excinfo:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM decision_revisions WHERE revision_id = 'rev-pg-1';")
        assert "strictly immutable" in str(excinfo.value)
        conn.rollback()

        with pytest.raises(Exception) as excinfo:
            with conn.cursor() as cur:
                cur.execute("UPDATE decision_evidences SET signature = 'tampered' WHERE evidence_id = 'ev-agg-1';")
        assert "strictly immutable" in str(excinfo.value)
        conn.rollback()

        with pytest.raises(Exception) as excinfo:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM decision_evidences WHERE evidence_id = 'ev-agg-1';")
        assert "strictly immutable" in str(excinfo.value)
        conn.rollback()

def test_postgres_active_leaf_projection_occ(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresActiveLeafProjectionRepository(conn)

        # 1. Save initial leaf
        updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        proj = ActiveLeafProjection("root-1", "root-1", 1, updated_at)
        repo.save_active_leaf(proj)

        loaded = repo.get_active_leaf("root-1")
        assert loaded is not None
        assert loaded.active_leaf_decision_id == "root-1"
        assert loaded.version == 1

        # 2. Save revision leaf under correct OCC
        proj2 = ActiveLeafProjection("root-1", "rev-1", 2, updated_at)
        repo.save_active_leaf(proj2)

        loaded2 = repo.get_active_leaf("root-1")
        assert loaded2.active_leaf_decision_id == "rev-1"
        assert loaded2.version == 2

        # 3. Trigger OCC Conflict (version mismatch)
        proj_stale = ActiveLeafProjection("root-1", "rev-2", 2, updated_at)
        with pytest.raises(ConcurrencyConflictError) as excinfo:
            repo.save_active_leaf(proj_stale)
        assert "Leaf version mismatch" in str(excinfo.value)

def test_postgres_exceptions(clean_db, snapshot):
    with clean_db.connection() as conn:
        repo = PostgresDecisionJournalRepository(conn)
        
        journal = DecisionJournalAggregate(
            decision_id="dec-dup",
            proposing_agent_id="agt-1",
            signature="sig-1",
            thesis_urn="urn:thesis:1",
            context_snapshot=snapshot,
            created_at=datetime.utcnow()
        )
        repo.save_journal(journal)
        
        with pytest.raises(ImmutabilityViolationException):
            with conn.transaction():
                repo.save_journal(journal)
            
        revision = DecisionRevisionAggregate(
            revision_id="rev-dup",
            parent_decision_id="dec-dup",
            root_decision_id="dec-dup",
            proposing_agent_id="agt-1",
            signature="sig-2",
            correction_reason="test",
            context_snapshot=snapshot,
            created_at=datetime.utcnow()
        )
        repo.save_revision(revision)
        
        with pytest.raises(ImmutabilityViolationException):
            with conn.transaction():
                repo.save_revision(revision)
            
        evidence_val = DecisionEvidence(
            evidence_id="ev-dup",
            description="test",
            artifact_ref=ArtifactReference("art-dup", "h", "u"),
            attached_at=datetime.utcnow()
        )
        evidence_agg = DecisionEvidenceAggregate(
            evidence_id="ev-agg-dup",
            decision_id="dec-dup",
            attached_by_agent_id="agt-1",
            signature="sig-ev",
            evidence=evidence_val,
            created_at=datetime.utcnow()
        )
        repo.save_evidence(evidence_agg)
        
        with pytest.raises(ImmutabilityViolationException):
            with conn.transaction():
                repo.save_evidence(evidence_agg)
