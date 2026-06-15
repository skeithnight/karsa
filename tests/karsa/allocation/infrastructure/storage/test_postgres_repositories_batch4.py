import pytest
import uuid
from datetime import datetime, timezone, timedelta
from testcontainers.postgres import PostgresContainer
from psycopg_pool import ConnectionPool
import psycopg

from karsa.allocation.domain.value_objects import (
    PortfolioHorizon,
    AllocationScore,
    RiskBudgetAssignment,
    AllocationRecommendation,
    AllocationMethodologyManifest
)
from karsa.allocation.domain.models import (
    AllocationSession,
    AllocationDecisionRecord,
    ImmutabilityViolationError
)
from karsa.allocation.infrastructure.storage.postgres_allocation_repositories import (
    PostgresAllocationSessionRepository,
    PostgresAllocationDecisionRecordRepository
)
from karsa.allocation.infrastructure.storage.in_memory_repositories import ConcurrencyConflictError
from karsa.allocation.application.service.allocation_services import (
    AllocationCalculationService,
    RankingProjectionService,
    AllocationReplayService,
    AllocationInvalidationService,
    MethodologyDriftException,
    ReplayIntegrityException
)

# Helpers
def make_horizon(horizon_id="90D"):
    return PortfolioHorizon(
        horizon_id=horizon_id,
        horizon_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        horizon_end=datetime(2026, 3, 31, tzinfo=timezone.utc)
    )

def make_score():
    return AllocationScore(
        raw_score=0.85,
        performance_score=0.9,
        attribution_score=1.05,
        review_penalty_multiplier=1.0
    )

def make_recommendation():
    risk = RiskBudgetAssignment(
        tracking_error_pct=0.05,
        max_drawdown_limit=0.15
    )
    return AllocationRecommendation(
        recommended_weight=0.25,
        recommended_capital_percentage=0.20,
        risk_budget=risk
    )

def make_manifest():
    return AllocationMethodologyManifest(
        allocation_methodology_urn="urn:karsa:allocation:methodology:m1",
        allocation_policy_hash="a" * 64,
        allocation_strategy_version="v1.0"
    )

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
            cur.execute("DROP TRIGGER IF EXISTS enforce_record_immutability ON allocation_decision_records;")
            cur.execute("DROP TABLE IF EXISTS allocation_decision_records_2026_q1 CASCADE;")
            cur.execute("DROP TABLE IF EXISTS allocation_decision_records_default CASCADE;")
            cur.execute("DROP TABLE IF EXISTS allocation_decision_records CASCADE;")
            cur.execute("DROP TABLE IF EXISTS allocation_sessions CASCADE;")
            cur.execute("DROP FUNCTION IF EXISTS block_allocation_record_mutation();")

            cur.execute("""
                CREATE OR REPLACE FUNCTION block_allocation_record_mutation()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF TG_OP = 'DELETE' THEN
                        RAISE EXCEPTION 'Allocation decision records are immutable and cannot be deleted.';
                    ELSIF TG_OP = 'UPDATE' THEN
                        IF NEW.record_id = OLD.record_id AND
                           NEW.record_urn = OLD.record_urn AND
                           NEW.session_urn = OLD.session_urn AND
                           NEW.worker_urn = OLD.worker_urn AND
                           NEW.decision_id = OLD.decision_id AND
                           NEW.horizon_id = OLD.horizon_id AND
                           NEW.horizon_start = OLD.horizon_start AND
                           NEW.horizon_end = OLD.horizon_end AND
                           NEW.raw_score = OLD.raw_score AND
                           NEW.performance_score = OLD.performance_score AND
                           NEW.attribution_score = OLD.attribution_score AND
                           NEW.review_penalty_multiplier = OLD.review_penalty_multiplier AND
                           NEW.recommended_weight = OLD.recommended_weight AND
                           NEW.recommended_capital_percentage = OLD.recommended_capital_percentage AND
                           NEW.tracking_error_pct = OLD.tracking_error_pct AND
                           NEW.max_drawdown_limit = OLD.max_drawdown_limit AND
                           NEW.allocation_methodology_urn = OLD.allocation_methodology_urn AND
                           NEW.allocation_policy_hash = OLD.allocation_policy_hash AND
                           NEW.allocation_strategy_version = OLD.allocation_strategy_version AND
                           NEW.allocation_manifest_hash = OLD.allocation_manifest_hash AND
                           NEW.calculated_at = OLD.calculated_at AND
                           NEW.allocation_version = OLD.allocation_version AND
                           (NEW.is_active = OLD.is_active OR (OLD.is_active = TRUE AND NEW.is_active = FALSE))
                        THEN
                            RETURN NEW;
                        ELSE
                            RAISE EXCEPTION 'Allocation decision records are immutable. Only deactivation and version lineage updates are allowed.';
                        END IF;
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)

            cur.execute("""
                CREATE TABLE allocation_sessions (
                    session_id UUID PRIMARY KEY,
                    session_urn VARCHAR(256) UNIQUE NOT NULL,
                    horizon_id VARCHAR(64) NOT NULL,
                    horizon_start TIMESTAMP WITH TIME ZONE NOT NULL,
                    horizon_end TIMESTAMP WITH TIME ZONE NOT NULL,
                    strategy_key VARCHAR(256) NOT NULL,
                    status VARCHAR(64) NOT NULL,
                    aggregate_version INTEGER NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE allocation_decision_records (
                    record_id UUID NOT NULL,
                    record_urn VARCHAR(256) NOT NULL,
                    session_urn VARCHAR(256) NOT NULL,
                    worker_urn VARCHAR(256) NOT NULL,
                    decision_id VARCHAR(256) NOT NULL,
                    horizon_id VARCHAR(64) NOT NULL,
                    horizon_start TIMESTAMP WITH TIME ZONE NOT NULL,
                    horizon_end TIMESTAMP WITH TIME ZONE NOT NULL,
                    raw_score DOUBLE PRECISION NOT NULL,
                    performance_score DOUBLE PRECISION NOT NULL,
                    attribution_score DOUBLE PRECISION NOT NULL,
                    review_penalty_multiplier DOUBLE PRECISION NOT NULL,
                    recommended_weight DOUBLE PRECISION NOT NULL,
                    recommended_capital_percentage DOUBLE PRECISION NOT NULL,
                    tracking_error_pct DOUBLE PRECISION NOT NULL,
                    max_drawdown_limit DOUBLE PRECISION NOT NULL,
                    allocation_methodology_urn VARCHAR(256) NOT NULL,
                    allocation_policy_hash VARCHAR(256) NOT NULL,
                    allocation_strategy_version VARCHAR(256) NOT NULL,
                    allocation_manifest_hash VARCHAR(256) NOT NULL,
                    supersedes_record_urn VARCHAR(256),
                    invalidates_record_urn VARCHAR(256),
                    is_active BOOLEAN NOT NULL,
                    superseded_by_version INTEGER,
                    invalidated_by_version INTEGER,
                    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    allocation_version INTEGER NOT NULL,
                    aggregate_version INTEGER NOT NULL,
                    PRIMARY KEY (record_id, calculated_at)
                ) PARTITION BY RANGE (calculated_at);

                CREATE TABLE allocation_decision_records_default PARTITION OF allocation_decision_records DEFAULT;
            """)

            cur.execute("""
                CREATE TRIGGER enforce_record_immutability
                BEFORE UPDATE OR DELETE ON allocation_decision_records
                FOR EACH ROW EXECUTE FUNCTION block_allocation_record_mutation();
            """)
    return postgres_pool

# MANDATORY TEST 1: OCC conflict integration test
def test_occ_conflict_integration(clean_db):
    with clean_db.connection() as conn:
        session_repo = PostgresAllocationSessionRepository(conn)
        record_repo = PostgresAllocationDecisionRecordRepository(conn)

        # 1. Session OCC conflict
        sess_id = str(uuid.uuid4())
        session = AllocationSession(
            session_id=sess_id,
            session_urn=f"urn:karsa:allocation:session:{sess_id}",
            horizon=make_horizon(),
            strategy_key="test-strategy"
        )
        session_repo.save(session)

        # Retrieve and update
        s1 = session_repo.find_by_urn(session.session_urn)
        s1.start()
        session_repo.save(s1)

        # Try to save stale
        session.status = "COMPLETED"
        session.increment_version()
        with pytest.raises(ConcurrencyConflictError):
            session_repo.save(session)

        # 2. Record OCC conflict
        rec_id = str(uuid.uuid4())
        m = make_manifest()
        record = AllocationDecisionRecord(
            record_id=rec_id,
            record_urn=f"urn:karsa:allocation:record:{rec_id}",
            session_urn=session.session_urn,
            worker_urn="urn:karsa:worker:w1",
            decision_id="dec-1",
            horizon=make_horizon(),
            allocation_score=make_score(),
            recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn,
            allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version,
            allocation_manifest_hash=m.compute_hash()
        )
        record_repo.save(record)

        r1 = record_repo.find_by_urn(record.record_urn)
        r1.supersede(next_version=2)
        record_repo.save(r1)

        record.supersede(next_version=2)
        with pytest.raises(ConcurrencyConflictError):
            record_repo.save(record)

# MANDATORY TEST 2: Lineage traversal integration test
def test_lineage_traversal_integration(clean_db):
    with clean_db.connection() as conn:
        record_repo = PostgresAllocationDecisionRecordRepository(conn)
        sess_urn = "urn:karsa:allocation:session:s1"
        m = make_manifest()

        # Chain: r1 -> r2 -> r3
        r1 = AllocationDecisionRecord(
            record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r1",
            session_urn=sess_urn, worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=make_horizon(), allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash(),
            is_active=False, superseded_by_version=2, allocation_version=1
        )
        r2 = AllocationDecisionRecord(
            record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r2",
            session_urn=sess_urn, worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=make_horizon(), allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash(),
            supersedes_record_urn=r1.record_urn, is_active=False, superseded_by_version=3, allocation_version=2
        )
        r3 = AllocationDecisionRecord(
            record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r3",
            session_urn=sess_urn, worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=make_horizon(), allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash(),
            supersedes_record_urn=r2.record_urn, is_active=True, allocation_version=3
        )

        record_repo.save(r1)
        record_repo.save(r2)
        record_repo.save(r3)

        # Lineage from r3
        chain = record_repo.find_lineage(r3.record_urn)
        assert len(chain) == 3
        assert chain[0].record_urn == r1.record_urn
        assert chain[1].record_urn == r2.record_urn
        assert chain[2].record_urn == r3.record_urn

        # Lineage alias check
        chain_alias = record_repo.find_allocation_lineage(r3.record_urn)
        assert len(chain_alias) == 3

        # Return empty list on missing
        assert record_repo.find_lineage("urn:karsa:allocation:record:missing") == []

# MANDATORY TEST 3: Replay success integration test
def test_replay_success_integration(clean_db):
    with clean_db.connection() as conn:
        record_repo = PostgresAllocationDecisionRecordRepository(conn)
        replay_service = AllocationReplayService(record_repo)
        m = make_manifest()

        record = AllocationDecisionRecord(
            record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r1",
            session_urn="urn:karsa:allocation:session:s1", worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=make_horizon(), allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash()
        )
        record_repo.save(record)

        assert replay_service.verify_replay(record.record_urn, m) is True

# MANDATORY TEST 4: Replay mismatch integration test
def test_replay_mismatch_integration(clean_db):
    with clean_db.connection() as conn:
        record_repo = PostgresAllocationDecisionRecordRepository(conn)
        replay_service = AllocationReplayService(record_repo)
        m = make_manifest()

        record = AllocationDecisionRecord(
            record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r1",
            session_urn="urn:karsa:allocation:session:s1", worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=make_horizon(), allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash()
        )
        record_repo.save(record)

        # Verification raises error on non-existent URN
        with pytest.raises(ValueError, match="AllocationDecisionRecord not found"):
            replay_service.verify_replay("urn:karsa:allocation:record:missing", m)

        # Verification raises error if manifest hash doesn't match metadata properties
        m_corrupted = AllocationMethodologyManifest(
            allocation_methodology_urn=m.allocation_methodology_urn,
            allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version
        )
        
        # We simulate hash mismatch by mocking compute_hash to return a different hash
        orig_compute_hash = AllocationMethodologyManifest.compute_hash
        def mock_compute_hash(self):
            if self is m_corrupted:
                return "corrupted_hash"
            return orig_compute_hash(self)

        import unittest.mock as mock
        with mock.patch("karsa.allocation.domain.value_objects.AllocationMethodologyManifest.compute_hash", new=mock_compute_hash):
            with pytest.raises(ReplayIntegrityException, match="Replay manifest hash mismatch"):
                replay_service.verify_replay(record.record_urn, m_corrupted)

# MANDATORY TEST 5: Methodology drift integration test
def test_methodology_drift_integration(clean_db):
    with clean_db.connection() as conn:
        record_repo = PostgresAllocationDecisionRecordRepository(conn)
        replay_service = AllocationReplayService(record_repo)
        m = make_manifest()

        record = AllocationDecisionRecord(
            record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r1",
            session_urn="urn:karsa:allocation:session:s1", worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=make_horizon(), allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash()
        )
        record_repo.save(record)

        # 1. Methodology URN drift
        m_urn = AllocationMethodologyManifest(
            allocation_methodology_urn="urn:karsa:allocation:methodology:other",
            allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version
        )
        with pytest.raises(MethodologyDriftException, match="Methodology URN drift"):
            replay_service.verify_replay(record.record_urn, m_urn)

        # 2. Policy hash drift
        m_policy = AllocationMethodologyManifest(
            allocation_methodology_urn=m.allocation_methodology_urn,
            allocation_policy_hash="b" * 64,
            allocation_strategy_version=m.allocation_strategy_version
        )
        with pytest.raises(MethodologyDriftException, match="Policy hash drift"):
            replay_service.verify_replay(record.record_urn, m_policy)

        # 3. Strategy version drift
        m_version = AllocationMethodologyManifest(
            allocation_methodology_urn=m.allocation_methodology_urn,
            allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version="v2.0"
        )
        with pytest.raises(MethodologyDriftException, match="Strategy version drift"):
            replay_service.verify_replay(record.record_urn, m_version)

# MANDATORY TEST 6: Trigger immutability integration test
def test_trigger_immutability_integration(clean_db):
    with clean_db.connection() as conn:
        record_repo = PostgresAllocationDecisionRecordRepository(conn)
        m = make_manifest()
        rid = str(uuid.uuid4())
        record = AllocationDecisionRecord(
            record_id=rid, record_urn=f"urn:karsa:allocation:record:{rid}",
            session_urn="urn:karsa:allocation:session:s1", worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=make_horizon(), allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash()
        )
        record_repo.save(record)

        # 1. Direct SQL update to raw_score should fail via trigger
        with pytest.raises((psycopg.Error, ImmutabilityViolationError)):
            with conn.transaction():
                cur = conn.cursor()
                cur.execute("UPDATE allocation_decision_records SET raw_score = 9.9 WHERE record_id = %s", (rid,))

        # 2. Direct SQL delete should fail via trigger
        with pytest.raises((psycopg.Error, ImmutabilityViolationError)):
            with conn.transaction():
                cur = conn.cursor()
                cur.execute("DELETE FROM allocation_decision_records WHERE record_id = %s", (rid,))

        # 3. Repository delete should fail via trigger mapping to ImmutabilityViolationError
        with pytest.raises(ImmutabilityViolationError):
            with conn.transaction():
                record_repo.delete(rid)

        # 4. Allowed transitions should pass: is_active -> FALSE
        record.supersede(next_version=2)
        record_repo.save(record)

        # Verify status updated
        updated = record_repo.find_by_urn(record.record_urn)
        assert updated.is_active is False
        assert updated.superseded_by_version == 2

# MANDATORY TEST 7: Partition routing integration test
def test_partition_routing_integration(clean_db):
    with clean_db.connection() as conn:
        with conn.cursor() as cur:
            # Create a specific partition for Q1 2026
            cur.execute("""
                CREATE TABLE IF NOT EXISTS allocation_decision_records_2026_q1 PARTITION OF allocation_decision_records
                FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2026-04-01 00:00:00+00');
            """)

        record_repo = PostgresAllocationDecisionRecordRepository(conn)
        m = make_manifest()

        # 1. Record within Q1 2026 range -> routes to allocation_decision_records_2026_q1
        dt_q1 = datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc)
        rid1 = str(uuid.uuid4())
        rec1 = AllocationDecisionRecord(
            record_id=rid1, record_urn=f"urn:karsa:allocation:record:{rid1}",
            session_urn="urn:karsa:allocation:session:s1", worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=make_horizon(), allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash(),
            allocated_at=dt_q1
        )
        record_repo.save(rec1)

        # 2. Record outside Q1 range (e.g. Q2 2026) -> routes to default partition
        dt_q2 = datetime(2026, 5, 20, 10, 0, 0, tzinfo=timezone.utc)
        rid2 = str(uuid.uuid4())
        rec2 = AllocationDecisionRecord(
            record_id=rid2, record_urn=f"urn:karsa:allocation:record:{rid2}",
            session_urn="urn:karsa:allocation:session:s1", worker_urn="urn:karsa:worker:w2", decision_id="dec-1",
            horizon=make_horizon(), allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash(),
            allocated_at=dt_q2
        )
        record_repo.save(rec2)

        # Verify counts directly in partition tables
        cur = conn.cursor()
        
        cur.execute("SELECT count(*) FROM allocation_decision_records_2026_q1")
        assert cur.fetchone()[0] == 1

        cur.execute("SELECT count(*) FROM allocation_decision_records_default")
        assert cur.fetchone()[0] == 1

# MANDATORY TEST 8: Deterministic ranking integration test
def test_deterministic_ranking_integration(clean_db):
    with clean_db.connection() as conn:
        record_repo = PostgresAllocationDecisionRecordRepository(conn)
        proj_service = RankingProjectionService()
        m = make_manifest()
        horizon = make_horizon()
        sess_urn = "urn:karsa:allocation:session:s1"

        brier_scores = {"urn:karsa:worker:A": 0.2, "urn:karsa:worker:B": 0.2, "urn:karsa:worker:C": 0.2}
        selection_returns = {"urn:karsa:worker:A": 0.1, "urn:karsa:worker:B": 0.1, "urn:karsa:worker:C": 0.1}
        review_scores = {"urn:karsa:worker:A": 0.9, "urn:karsa:worker:B": 0.9, "urn:karsa:worker:C": 0.9}

        # Save records for A, B, C (all scores identical, sorted alphabetically A, B, C)
        recs = {}
        for name in ("A", "B", "C"):
            rid = str(uuid.uuid4())
            recs[name] = AllocationDecisionRecord(
                record_id=rid, record_urn=f"urn:karsa:allocation:record:{name.lower()}",
                session_urn=sess_urn, worker_urn=f"urn:karsa:worker:{name}", decision_id="dec-1",
                horizon=horizon, allocation_score=AllocationScore(0.8, 1.0, 1.0, 1.0),
                recommendation=make_recommendation(), allocation_methodology_urn=m.allocation_methodology_urn,
                allocation_policy_hash=m.allocation_policy_hash, allocation_strategy_version=m.allocation_strategy_version,
                allocation_manifest_hash=m.compute_hash()
            )
            record_repo.save(recs[name])

        # Query and project with input order A, B, C
        records_abc = [recs["A"], recs["B"], recs["C"]]
        proj_abc = proj_service.build_ranking_projection(
            sess_urn, horizon, records_abc, brier_scores, selection_returns, review_scores
        )

        # Query and project with input order C, B, A
        records_cba = [recs["C"], recs["B"], recs["A"]]
        proj_cba = proj_service.build_ranking_projection(
            sess_urn, horizon, records_cba, brier_scores, selection_returns, review_scores
        )

        # Asserts identical outcomes
        assert len(proj_abc.rankings) == 3
        assert len(proj_cba.rankings) == 3
        for i in range(3):
            assert proj_abc.rankings[i].worker_urn == proj_cba.rankings[i].worker_urn
            assert proj_abc.rankings[i].rank_index == proj_cba.rankings[i].rank_index

# MANDATORY TEST 9: Allocation invalidation integration test
def test_allocation_invalidation_integration(clean_db):
    with clean_db.connection() as conn:
        record_repo = PostgresAllocationDecisionRecordRepository(conn)
        invalidation_service = AllocationInvalidationService(record_repo)
        sess_urn = "urn:karsa:allocation:session:s1"
        m = make_manifest()

        # Chain: r1 -> r2 -> r3
        r1 = AllocationDecisionRecord(
            record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r1",
            session_urn=sess_urn, worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=make_horizon(), allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash(),
            is_active=False, superseded_by_version=2, allocation_version=1
        )
        r2 = AllocationDecisionRecord(
            record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r2",
            session_urn=sess_urn, worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=make_horizon(), allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash(),
            supersedes_record_urn=r1.record_urn, is_active=True, allocation_version=2
        )

        record_repo.save(r1)
        record_repo.save(r2)

        # Invalidate starting from r2
        invalidated = invalidation_service.invalidate_lineage(r2.record_urn, invalidating_version=99)
        assert len(invalidated) == 1
        assert invalidated[0].record_urn == r2.record_urn
        assert invalidated[0].is_active is False
        assert invalidated[0].invalidated_by_version == 99

        # Verify it was saved to DB as invalidated
        db_rec = record_repo.find_by_urn(r2.record_urn)
        assert db_rec.is_active is False
        assert db_rec.invalidated_by_version == 99

        # Immutable history: r1 remained unmodified
        db_r1 = record_repo.find_by_urn(r1.record_urn)
        assert db_r1.is_active is False
        assert db_r1.superseded_by_version == 2
        assert db_r1.invalidated_by_version is None

# MANDATORY TEST 10: Supersession chain integration test
def test_supersession_chain_integration(clean_db):
    with clean_db.connection() as conn:
        record_repo = PostgresAllocationDecisionRecordRepository(conn)
        sess_repo = PostgresAllocationSessionRepository(conn)
        calc_service = AllocationCalculationService(record_repo, sess_repo)

        # Setup active session
        sess_id = str(uuid.uuid4())
        session = AllocationSession(
            session_id=sess_id,
            session_urn=f"urn:karsa:allocation:session:{sess_id}",
            horizon=make_horizon(),
            strategy_key="test-strategy"
        )
        session.start()
        sess_repo.save(session)

        # Compute first version
        r1 = calc_service.calculate_allocations(
            session_urn=session.session_urn, worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            raw_score=0.8, brier_score=0.15, selection_return=0.05, review_score=0.9, has_warning=False,
            allocation_methodology_urn="urn:karsa:allocation:methodology:m1", allocation_policy_hash="a" * 64,
            allocation_strategy_version="v1.0"
        )

        # Compute second version (should supersede first)
        r2 = calc_service.calculate_allocations(
            session_urn=session.session_urn, worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            raw_score=0.85, brier_score=0.12, selection_return=0.06, review_score=0.92, has_warning=False,
            allocation_methodology_urn="urn:karsa:allocation:methodology:m1", allocation_policy_hash="a" * 64,
            allocation_strategy_version="v1.0"
        )

        assert r1.record_urn is not None
        assert r2.record_urn is not None
        assert r2.supersedes_record_urn == r1.record_urn
        assert r2.allocation_version == 2

        # Verify DB states
        db_r1 = record_repo.find_by_urn(r1.record_urn)
        db_r2 = record_repo.find_by_urn(r2.record_urn)
        assert db_r1.is_active is False
        assert db_r1.superseded_by_version == 2
        assert db_r2.is_active is True
        assert db_r2.allocation_version == 2

# Cycle detection and pagination tests to ensure complete requirements & coverage coverage
def test_lineage_cycle_detection(clean_db):
    with clean_db.connection() as conn:
        record_repo = PostgresAllocationDecisionRecordRepository(conn)
        sess_urn = "urn:karsa:allocation:session:s1"
        m = make_manifest()

        # Create records that reference each other in a loop
        # r1 -> r2 -> r1
        r1 = AllocationDecisionRecord(
            record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r1",
            session_urn=sess_urn, worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=make_horizon(), allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash(),
            invalidates_record_urn="urn:karsa:allocation:record:r2", is_active=True
        )
        r2 = AllocationDecisionRecord(
            record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r2",
            session_urn=sess_urn, worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=make_horizon(), allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash(),
            supersedes_record_urn=r1.record_urn, is_active=True
        )

        record_repo.save(r1)
        record_repo.save(r2)

        # Lineage retrieval must not result in an infinite loop due to cycle visited protection
        chain = record_repo.find_lineage(r1.record_urn)
        assert len(chain) == 2

def test_pagination_keyset(clean_db):
    with clean_db.connection() as conn:
        record_repo = PostgresAllocationDecisionRecordRepository(conn)
        m = make_manifest()
        sess_urn = "urn:karsa:allocation:session:s1"

        # Create multiple active records for the same worker
        for i in range(5):
            rid = str(uuid.uuid4())
            # Use deterministic naming to sorting alphabetically
            rec = AllocationDecisionRecord(
                record_id=rid, record_urn=f"urn:karsa:allocation:record:worker1:{i}",
                session_urn=sess_urn, worker_urn="urn:karsa:worker:worker1", decision_id=f"dec-{i}",
                horizon=make_horizon(), allocation_score=make_score(), recommendation=make_recommendation(),
                allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
                allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash(),
                is_active=True
            )
            record_repo.save(rec)

        # Fetch first page of 2
        page1 = record_repo.find_active_by_worker("urn:karsa:worker:worker1", limit=2)
        assert len(page1) == 2
        assert page1[0].record_urn == "urn:karsa:allocation:record:worker1:0"
        assert page1[1].record_urn == "urn:karsa:allocation:record:worker1:1"

        # Fetch second page of 2 using page1[1].record_urn as cursor
        page2 = record_repo.find_active_by_worker("urn:karsa:worker:worker1", limit=2, cursor=page1[1].record_urn)
        assert len(page2) == 2
        assert page2[0].record_urn == "urn:karsa:allocation:record:worker1:2"
        assert page2[1].record_urn == "urn:karsa:allocation:record:worker1:3"

        # Fetch session records paginated
        sess_page1 = record_repo.find_by_session_paginated(sess_urn, limit=2)
        assert len(sess_page1) == 2
        assert sess_page1[0].record_urn == "urn:karsa:allocation:record:worker1:0"
        assert sess_page1[1].record_urn == "urn:karsa:allocation:record:worker1:1"

        sess_page2 = record_repo.find_by_session_paginated(sess_urn, limit=2, cursor=sess_page1[1].record_urn)
        assert len(sess_page2) == 2
        assert sess_page2[0].record_urn == "urn:karsa:allocation:record:worker1:2"
        assert sess_page2[1].record_urn == "urn:karsa:allocation:record:worker1:3"

def test_postgres_repositories_extra_coverage(clean_db):
    with clean_db.connection() as conn:
        session_repo = PostgresAllocationSessionRepository(conn)
        record_repo = PostgresAllocationDecisionRecordRepository(conn)
        m = make_manifest()
        sess_urn = "urn:karsa:allocation:session:s1"
        horizon = make_horizon()

        # 1. find_by_urn missing session -> returns None
        assert session_repo.find_by_urn("urn:karsa:allocation:session:nonexistent") is None

        # Create and save a record
        rid = str(uuid.uuid4())
        record = AllocationDecisionRecord(
            record_id=rid, record_urn=f"urn:karsa:allocation:record:{rid}",
            session_urn=sess_urn, worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=horizon, allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash()
        )
        record_repo.save(record)

        # 2. Reactivate inactive record -> raise ImmutabilityViolationError
        record.supersede(next_version=2)
        record_repo.save(record)

        record_active = AllocationDecisionRecord(
            record_id=rid, record_urn=f"urn:karsa:allocation:record:{rid}",
            session_urn=sess_urn, worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=horizon, allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash(),
            is_active=True,
            allocated_at=record.allocated_at,
            aggregate_version=3
        )
        with pytest.raises(ImmutabilityViolationError, match="Cannot reactivate an inactive record"):
            record_repo.save(record_active)

        # 3. Modify calculated_at -> raise ImmutabilityViolationError
        record_diff_time = AllocationDecisionRecord(
            record_id=rid, record_urn=f"urn:karsa:allocation:record:{rid}",
            session_urn=sess_urn, worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=horizon, allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash(),
            is_active=False,
            allocated_at=datetime.now(timezone.utc) + timedelta(days=1),
            aggregate_version=3
        )
        with pytest.raises(ImmutabilityViolationError, match="Cannot modify immutable field 'calculated_at'"):
            record_repo.save(record_diff_time)

        # 4. Modify raw_score -> raise ImmutabilityViolationError
        record_diff_score = AllocationDecisionRecord(
            record_id=rid, record_urn=f"urn:karsa:allocation:record:{rid}",
            session_urn=sess_urn, worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=horizon, allocation_score=AllocationScore(99.0, 1.0, 1.0, 1.0), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash(),
            is_active=False,
            allocated_at=record.allocated_at,
            aggregate_version=3
        )
        with pytest.raises(ImmutabilityViolationError, match="Cannot modify immutable field 'raw_score'"):
            record_repo.save(record_diff_score)

        # 5. Mock psycopg.Error during delete (returns psycopg.DatabaseError)
        import unittest.mock as mock
        mock_cur = mock.MagicMock()
        def side_effect_execute_std(query, params=None):
            if "DELETE" in query or "UPDATE" in query or "INSERT" in query:
                raise psycopg.DatabaseError("generic database error")
        mock_cur.execute.side_effect = side_effect_execute_std
        with mock.patch.object(conn, "cursor", return_value=mock_cur):
            with pytest.raises(psycopg.DatabaseError, match="generic database error"):
                record_repo.delete(rid)

        # 6. Mock psycopg.Error containing "immutable" during update (raises ImmutabilityViolationError)
        mock_cur_immutable = mock.MagicMock()
        def side_effect_execute_imm(query, params=None):
            if "UPDATE" in query or "INSERT" in query:
                raise psycopg.DatabaseError("immutable trigger violation error")
        mock_cur_immutable.execute.side_effect = side_effect_execute_imm
        mock_cur_immutable.fetchone.return_value = (2, True, 0.85, 0.9, 1.05, 1.0, 0.25, 0.20, 0.05, 0.15, "urn:karsa:worker:w1", record.allocated_at, m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash())
        with mock.patch.object(conn, "cursor", return_value=mock_cur_immutable):
            with pytest.raises(ImmutabilityViolationError, match="immutable trigger violation error"):
                record_repo.save(record_active)

        # 7. Mock psycopg.Error containing "immutable" during insert (raises ImmutabilityViolationError)
        rid_new = str(uuid.uuid4())
        record_new = AllocationDecisionRecord(
            record_id=rid_new, record_urn=f"urn:karsa:allocation:record:{rid_new}",
            session_urn=sess_urn, worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
            horizon=horizon, allocation_score=make_score(), recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn, allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version, allocation_manifest_hash=m.compute_hash()
        )
        mock_cur_immutable.fetchone.return_value = None  # to force insert path
        with mock.patch.object(conn, "cursor", return_value=mock_cur_immutable):
            with pytest.raises(ImmutabilityViolationError, match="immutable trigger violation error"):
                record_repo.save(record_new)

        # 8. Rowcount == 0 updates for session and record
        mock_cur_rowcount = mock.MagicMock()
        mock_cur_rowcount.rowcount = 0
        def side_effect_fetchone():
            return (1, True, 0.85, 0.9, 1.05, 1.0, 0.25, 0.20, 0.05, 0.15, "urn:karsa:worker:w1", record.allocated_at, m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash())
        mock_cur_rowcount.fetchone.side_effect = side_effect_fetchone
        with mock.patch.object(conn, "cursor", return_value=mock_cur_rowcount):
            # Session rowcount == 0
            session = AllocationSession(
                session_id=str(uuid.uuid4()),
                session_urn="urn:karsa:allocation:session:srowcount",
                horizon=horizon,
                strategy_key="test"
            )
            session.status = "CALCULATING"
            session.aggregate_version = 2
            with pytest.raises(ConcurrencyConflictError, match="Concurrency update failed on session"):
                session_repo.save(session)

            # Record rowcount == 0
            record_active.aggregate_version = 2
            with pytest.raises(ConcurrencyConflictError, match="Concurrency update failed on record"):
                record_repo.save(record_active)

        # 9. Mock psycopg.Error (generic) during update
        record_active.aggregate_version = 3
        with mock.patch.object(conn, "cursor", return_value=mock_cur):
            mock_cur.fetchone.return_value = (2, True, 0.85, 0.9, 1.05, 1.0, 0.25, 0.20, 0.05, 0.15, "urn:karsa:worker:w1", record.allocated_at, m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash())
            with pytest.raises(psycopg.DatabaseError, match="generic database error"):
                record_repo.save(record_active)

        # 10. Mock psycopg.Error (generic) during insert
        mock_cur.fetchone.return_value = None  # force insert path
        with mock.patch.object(conn, "cursor", return_value=mock_cur):
            with pytest.raises(psycopg.DatabaseError, match="generic database error"):
                record_repo.save(record_new)
