import sys
import types
import pytest
import uuid
import psycopg
from datetime import datetime, timezone
from testcontainers.postgres import PostgresContainer
from psycopg_pool import ConnectionPool

# Mock alembic.op module and configure alembic package path
import os
alembic_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../alembic"))
if "alembic" not in sys.modules:
    alembic_pkg = types.ModuleType("alembic")
    alembic_pkg.__path__ = [alembic_path]
    sys.modules["alembic"] = alembic_pkg
    
    alembic_op = types.ModuleType("alembic.op")
    sys.modules["alembic.op"] = alembic_op
    alembic_pkg.op = alembic_op

if "sqlalchemy" not in sys.modules:
    sys.modules["sqlalchemy"] = types.ModuleType("sqlalchemy")

import alembic.op

from karsa.review.domain.models import ReviewSession, ReviewRecord, PostMortemRecord
from karsa.review.domain.value_objects import (
    DecisionQualityAssessment,
    FailureClassification,
    SuccessClassification,
    ImprovementRecommendation,
    ReviewMethodologyManifest
)
from karsa.review.infrastructure.postgres_repositories import (
    PostgresReviewSessionRepository,
    PostgresReviewRecordRepository,
    PostgresPostMortemRecordRepository
)
from karsa.review.application.services_batch3 import (
    ReviewRecordingService,
    ReviewReplayService,
    ConsensusSolver,
    PostMortemService,
    ReviewInvalidationService,
    MethodologyDriftException,
    ReplayIntegrityException,
    serialize_and_hash_inputs
)
from karsa.review.infrastructure.repositories_batch2 import ConcurrencyConflictError


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
            # Drop tables first
            cur.execute("DROP TRIGGER IF EXISTS enforce_postmortem_record_immutability ON postmortem_records;")
            cur.execute("DROP TRIGGER IF EXISTS enforce_review_record_immutability ON review_records;")
            cur.execute("DROP TABLE IF EXISTS postmortem_records_default CASCADE;")
            cur.execute("DROP TABLE IF EXISTS postmortem_records CASCADE;")
            cur.execute("DROP TABLE IF EXISTS review_records_default CASCADE;")
            cur.execute("DROP TABLE IF EXISTS review_records CASCADE;")
            cur.execute("DROP TABLE IF EXISTS review_sessions CASCADE;")
            cur.execute("DROP FUNCTION IF EXISTS block_postmortem_record_mutation() CASCADE;")
            cur.execute("DROP FUNCTION IF EXISTS block_review_record_mutation() CASCADE;")
            conn.commit()
            
            # Mock alembic.op.execute
            alembic.op.execute = cur.execute
            
            import importlib
            migration = importlib.import_module("alembic.versions.44_review_postmortem_init")
            migration.upgrade()
            conn.commit()
            
    return postgres_pool


# Helper constructors
def make_session(status="INITIATED", raw_input_hash=None):
    sess_id = str(uuid.uuid4())
    return ReviewSession(
        session_id=sess_id,
        session_urn=f"urn:karsa:review:session:{sess_id}",
        horizon_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        horizon_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
        raw_input_manifest_hash=raw_input_hash or "a" * 64,
        status=status
    )


def make_record(session_urn, decision_id="dec-1", worker_urn="urn:karsa:worker:w1", review_version=1):
    rec_id = str(uuid.uuid4())
    manifest = ReviewMethodologyManifest("urn:karsa:m:1", "b" * 64, "v1", "gpt-4")
    dq = DecisionQualityAssessment(0.8, 0.9, 0.1)
    return ReviewRecord(
        record_id=rec_id,
        record_urn=f"urn:karsa:review:record:{rec_id}",
        session_urn=session_urn,
        decision_id=decision_id,
        worker_urn=worker_urn,
        review_methodology_urn="urn:karsa:m:1",
        review_policy_hash="b" * 64,
        review_prompt_version="v1",
        reviewer_model_version="gpt-4",
        review_methodology_manifest_hash=manifest.compute_hash(),
        decision_quality=dq,
        reviewed_at=datetime.now(timezone.utc),
        review_version=review_version
    )


def make_postmortem(session_urn, decision_id="dec-1", postmortem_version=1):
    pm_id = str(uuid.uuid4())
    fc = FailureClassification(True, False, False, False, False)
    sc = SuccessClassification(False, True, False)
    rec = ImprovementRecommendation("EXECUTION_WARNING", "exec", "LOW")
    return PostMortemRecord(
        postmortem_id=pm_id,
        postmortem_urn=f"urn:karsa:postmortem:record:{pm_id}",
        session_urn=session_urn,
        decision_id=decision_id,
        consensus_methodology_urn="urn:karsa:consensus:s1",
        consensus_policy_hash="c" * 64,
        input_review_record_urns=["urn:karsa:review:record:r1"],
        failure_classification=fc,
        success_classification=sc,
        recommendation=rec,
        created_at=datetime.now(timezone.utc),
        postmortem_version=postmortem_version
    )


# 1. POSTGRES REPOSITORIES INTEGRATION FLOWS
def test_postgres_review_session_repository_flow(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresReviewSessionRepository(conn)
        
        # Save Session
        sess = make_session()
        repo.save(sess)
        
        # Find Session
        loaded = repo.find_by_id(sess.session_id)
        assert loaded is not None
        assert loaded.session_urn == sess.session_urn
        
        loaded_urn = repo.find_by_urn(sess.session_urn)
        assert loaded_urn is not None
        assert loaded_urn.session_id == sess.session_id
        
        # OCC Check
        sess.aggregate_version = 2
        repo.save(sess)
        assert repo.find_by_id(sess.session_id).aggregate_version == 2
        
        # OCC Conflict
        sess.aggregate_version = 1
        with pytest.raises(ConcurrencyConflictError):
            repo.save(sess)


def test_postgres_review_record_repository_flow(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresReviewRecordRepository(conn)
        sess_repo = PostgresReviewSessionRepository(conn)
        
        sess = make_session(status="CONDUCTING")
        sess_repo.save(sess)
        
        rec = make_record(sess.session_urn)
        repo.save(rec)
        
        loaded = repo.find_by_id(rec.record_id)
        assert loaded is not None
        assert loaded.record_urn == rec.record_urn
        
        loaded_urn = repo.find_by_urn(rec.record_urn)
        assert loaded_urn is not None
        
        # find_active_by_worker
        active = repo.find_active_by_worker(rec.worker_urn, limit=10)
        assert len(active) == 1
        assert active[0].record_id == rec.record_id
        
        # find_by_session_paginated
        paginated = repo.find_by_session_paginated(sess.session_urn, limit=10)
        assert len(paginated) == 1
        
        # OCC conflict
        rec.aggregate_version = 1
        with pytest.raises(ConcurrencyConflictError):
            repo.save(rec)


def test_postgres_postmortem_record_repository_flow(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresPostMortemRecordRepository(conn)
        sess_repo = PostgresReviewSessionRepository(conn)
        
        sess = make_session(status="CONDUCTING")
        sess_repo.save(sess)
        
        pm = make_postmortem(sess.session_urn)
        repo.save(pm)
        
        loaded = repo.find_by_id(pm.postmortem_id)
        assert loaded is not None
        assert loaded.postmortem_urn == pm.postmortem_urn
        
        # Valid Update via supersede
        pm.supersede(next_version=2)
        repo.save(pm)
        assert repo.find_by_id(pm.postmortem_id).is_active is False
        
        # OCC Conflict
        # Since DB version is now 2, setting aggregate_version back to 1 triggers ConcurrencyConflictError
        pm.aggregate_version = 1
        with pytest.raises(ConcurrencyConflictError):
            repo.save(pm)


# 2. TRIGGERS IMMUTABILITY TESTS
def test_review_record_immutability_triggers(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresReviewRecordRepository(conn)
        sess_repo = PostgresReviewSessionRepository(conn)
        
        sess = make_session(status="CONDUCTING")
        sess_repo.save(sess)
        
        rec = make_record(sess.session_urn)
        repo.save(rec)
        conn.commit()

        # Attempt to delete must fail
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute("DELETE FROM review_records WHERE record_id = %s", (rec.record_id,))
            conn.rollback()

        # Attempt to mutate forbidden columns must fail:
        forbidden_cols = [
            ("worker_urn", "'urn:karsa:worker:mutated'"),
            ("record_urn", "'urn:karsa:review:record:mutated'"),
            ("session_urn", "'urn:karsa:review:session:mutated'"),
            ("review_methodology_urn", "'urn:karsa:review:methodology:mutated'"),
            ("outcome_independent_score", "0.999"),
            ("outcome_dependent_score", "0.999"),
            ("hindsight_bias_deviation", "0.999"),
            ("reviewed_at", "'2026-01-01 00:00:00'::timestamp"),
        ]
        for col, val in forbidden_cols:
            with conn.cursor() as cur:
                with pytest.raises(psycopg.errors.RaiseException):
                    cur.execute(f"UPDATE review_records SET {col} = {val} WHERE record_id = %s", (rec.record_id,))
                conn.rollback()

        # Mutate allowed fields (is_active, superseded_by_version, invalidated_by_version, aggregate_version) must succeed
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE review_records
                SET is_active = FALSE, superseded_by_version = 2, invalidated_by_version = 3, aggregate_version = 2
                WHERE record_id = %s
                """,
                (rec.record_id,)
            )
            conn.commit()

        fetched = repo.find_by_id(rec.record_id)
        assert fetched.is_active is False
        assert fetched.superseded_by_version == 2
        assert fetched.invalidated_by_version == 3
        assert fetched.aggregate_version == 2


def test_postmortem_record_immutability_triggers(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresPostMortemRecordRepository(conn)
        sess_repo = PostgresReviewSessionRepository(conn)
        
        sess = make_session(status="CONDUCTING")
        sess_repo.save(sess)
        
        pm = make_postmortem(sess.session_urn)
        repo.save(pm)
        conn.commit()

        # Attempt to delete must fail
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute("DELETE FROM postmortem_records WHERE postmortem_id = %s", (pm.postmortem_id,))
            conn.rollback()

        # Attempt to mutate forbidden columns must fail
        forbidden_cols = [
            ("decision_id", "'mutated'"),
            ("postmortem_urn", "'urn:karsa:postmortem:record:mutated'"),
            ("session_urn", "'urn:karsa:review:session:mutated'"),
            ("consensus_methodology_urn", "'urn:karsa:consensus:mutated'"),
            ("thesis_error", "FALSE"),
            ("execution_error", "TRUE"),
            ("timing_error", "TRUE"),
            ("sizing_error", "TRUE"),
            ("calibration_error", "TRUE"),
            ("alpha_generation", "TRUE"),
            ("execution_efficiency", "FALSE"),
            ("risk_mitigation", "TRUE"),
            ("recommendation_code", "'mutated'"),
            ("recommendation_category", "'mutated'"),
            ("recommendation_severity", "'mutated'"),
            ("created_at", "'2026-01-01 00:00:00'::timestamp"),
        ]
        for col, val in forbidden_cols:
            with conn.cursor() as cur:
                with pytest.raises(psycopg.errors.RaiseException):
                    cur.execute(f"UPDATE postmortem_records SET {col} = {val} WHERE postmortem_id = %s", (pm.postmortem_id,))
                conn.rollback()

        # Mutate allowed fields must succeed
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE postmortem_records
                SET is_active = FALSE, superseded_by_version = 2, invalidated_by_version = 3, aggregate_version = 2
                WHERE postmortem_id = %s
                """,
                (pm.postmortem_id,)
            )
            conn.commit()

        fetched = repo.find_by_id(pm.postmortem_id)
        assert fetched.is_active is False
        assert fetched.superseded_by_version == 2
        assert fetched.invalidated_by_version == 3
        assert fetched.aggregate_version == 2


# 3. REPLAYABILITY INTEGRATION TESTS
def test_replay_review_success(clean_db):
    with clean_db.connection() as conn:
        sess_repo = PostgresReviewSessionRepository(conn)
        record_repo = PostgresReviewRecordRepository(conn)
        
        recording_service = ReviewRecordingService(record_repo, sess_repo)
        replay_service = ReviewReplayService(record_repo, sess_repo)

        # Seed data
        decision_journal = {"trade_id": "t1", "action": "BUY"}
        performance = {"realized_pnl": 1500.0}
        attribution = {"market_factor": 0.2}

        raw_manifest_hash = serialize_and_hash_inputs(decision_journal, performance, attribution)

        session = make_session(status="CONDUCTING", raw_input_hash=raw_manifest_hash)
        sess_repo.save(session)

        dq = DecisionQualityAssessment(0.8, 0.9, 0.1)
        manifest = ReviewMethodologyManifest("urn:karsa:m:1", "b" * 64, "v1", "gpt-4")

        record = recording_service.record_review(
            record_id=str(uuid.uuid4()),
            record_urn=f"urn:karsa:review:record:{str(uuid.uuid4())}",
            session_urn=session.session_urn,
            decision_id="dec-1",
            worker_urn="urn:karsa:worker:w1",
            review_methodology_urn="urn:karsa:m:1",
            review_policy_hash="b" * 64,
            review_prompt_version="v1",
            reviewer_model_version="gpt-4",
            review_methodology_manifest_hash=manifest.compute_hash(),
            decision_quality=dq,
            reviewed_at=datetime.now(timezone.utc)
        )
        conn.commit()

        # Verify replay integrity
        replay_service.verify_replay_integrity(session.session_urn, decision_journal, performance, attribution)

        # Verify methodology manifest
        replay_service.verify_methodology_manifest(record)


def test_replay_methodology_drift_and_mismatch(clean_db):
    with clean_db.connection() as conn:
        sess_repo = PostgresReviewSessionRepository(conn)
        record_repo = PostgresReviewRecordRepository(conn)
        
        recording_service = ReviewRecordingService(record_repo, sess_repo)
        replay_service = ReviewReplayService(record_repo, sess_repo)

        decision_journal = {"trade_id": "t1"}
        performance = {"pnl": 100}
        attribution = {"alpha": 1}
        raw_manifest_hash = serialize_and_hash_inputs(decision_journal, performance, attribution)

        session = make_session(status="CONDUCTING", raw_input_hash=raw_manifest_hash)
        sess_repo.save(session)

        dq = DecisionQualityAssessment(0.8, 0.9, 0.1)
        manifest = ReviewMethodologyManifest("urn:karsa:m:1", "b" * 64, "v1", "gpt-4")

        record = recording_service.record_review(
            record_id=str(uuid.uuid4()),
            record_urn=f"urn:karsa:review:record:{str(uuid.uuid4())}",
            session_urn=session.session_urn,
            decision_id="dec-1",
            worker_urn="urn:karsa:worker:w1",
            review_methodology_urn="urn:karsa:m:1",
            review_policy_hash="b" * 64,
            review_prompt_version="v1",
            reviewer_model_version="gpt-4",
            review_methodology_manifest_hash=manifest.compute_hash(),
            decision_quality=dq,
            reviewed_at=datetime.now(timezone.utc)
        )
        conn.commit()

        # Replay mismatch detection
        different_attr = {"alpha": 0}
        with pytest.raises(ReplayIntegrityException):
            replay_service.verify_replay_integrity(session.session_urn, decision_journal, performance, different_attr)

        # Methodology drift detection (by overriding __dict__ to simulate drift)
        record.__dict__["review_prompt_version"] = "v2"
        with pytest.raises(MethodologyDriftException):
            replay_service.verify_methodology_manifest(record)


# 4. LINEAGE INTEGRATION TESTS
def test_postgres_review_lineage_reconstruction(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresReviewRecordRepository(conn)
        sess_repo = PostgresReviewSessionRepository(conn)

        sess = make_session(status="CONDUCTING")
        sess_repo.save(sess)

        r1 = make_record(sess.session_urn, review_version=1)
        r1.is_active = False
        r1.superseded_by_version = 2
        repo.save(r1)

        r2 = make_record(sess.session_urn, decision_id=r1.decision_id, worker_urn=r1.worker_urn, review_version=2)
        r2.is_active = False
        r2.superseded_by_version = 3
        repo.save(r2)

        r3 = make_record(sess.session_urn, decision_id=r1.decision_id, worker_urn=r1.worker_urn, review_version=3)
        r3.is_active = True
        repo.save(r3)
        conn.commit()

        lineage = repo.find_review_lineage(r1.record_urn)
        assert len(lineage) == 3
        assert lineage[0].review_version == 1
        assert lineage[1].review_version == 2
        assert lineage[2].review_version == 3


def test_postgres_postmortem_lineage_reconstruction(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresPostMortemRecordRepository(conn)
        sess_repo = PostgresReviewSessionRepository(conn)

        sess = make_session(status="CONDUCTING")
        sess_repo.save(sess)

        pm1 = make_postmortem(sess.session_urn, postmortem_version=1)
        pm1.is_active = False
        pm1.superseded_by_version = 2
        repo.save(pm1)

        pm2 = make_postmortem(sess.session_urn, decision_id=pm1.decision_id, postmortem_version=2)
        pm2.is_active = True
        repo.save(pm2)
        conn.commit()

        lineage = repo.find_postmortem_lineage(pm1.postmortem_urn)
        assert len(lineage) == 2
        assert lineage[0].postmortem_version == 1
        assert lineage[1].postmortem_version == 2


def test_postgres_lineage_cycle_detection(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresReviewRecordRepository(conn)
        sess_repo = PostgresReviewSessionRepository(conn)

        sess = make_session(status="CONDUCTING")
        sess_repo.save(sess)

        r1 = make_record(sess.session_urn, review_version=1)
        r1.is_active = False
        r1.superseded_by_version = 2
        repo.save(r1)

        r2 = make_record(sess.session_urn, decision_id=r1.decision_id, worker_urn=r1.worker_urn, review_version=2)
        r2.is_active = False
        r2.superseded_by_version = 1  # Cycle back to 1
        repo.save(r2)
        conn.commit()

        lineage = repo.find_review_lineage(r1.record_urn)
        assert len(lineage) == 2  # terminates safely due to visited set loop protection


# 5. CONSENSUS SOLVER & POST-MORTEM INTEGRATION TESTS
def test_postgres_consensus_solver_and_postmortem_flows(clean_db):
    with clean_db.connection() as conn:
        sess_repo = PostgresReviewSessionRepository(conn)
        record_repo = PostgresReviewRecordRepository(conn)
        pm_repo = PostgresPostMortemRecordRepository(conn)

        solver = ConsensusSolver()
        pm_service = PostMortemService(pm_repo, record_repo, solver)

        sess = make_session(status="CONDUCTING")
        sess_repo.save(sess)

        r1 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w1")
        r2 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w2")
        r3 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w3")
        record_repo.save(r1)
        record_repo.save(r2)
        record_repo.save(r3)
        conn.commit()

        fc1 = FailureClassification(True, False, False, False, False)
        fc2 = FailureClassification(True, True, False, False, False)
        fc3 = FailureClassification(False, True, False, False, False)
        
        sc1 = SuccessClassification(True, False, True)
        sc2 = SuccessClassification(True, True, False)
        sc3 = SuccessClassification(False, False, False)
        
        # Test qualitative codes
        rec1 = ImprovementRecommendation("THESIS_REVIEW_REQUIRED", "t", "HIGH", ["Action A"])
        rec2 = ImprovementRecommendation("EXECUTION_WARNING", "e", "MEDIUM", ["Action B"])
        rec3 = ImprovementRecommendation("THESIS_REVIEW_REQUIRED", "t", "HIGH", ["Action A", "Action C"])

        # 1. Deterministic Replay and Weighted Majority Check
        pm = pm_service.finalize_postmortem(
            postmortem_id=str(uuid.uuid4()),
            postmortem_urn=f"urn:karsa:postmortem:record:{str(uuid.uuid4())}",
            session_urn=sess.session_urn,
            decision_id="dec-1",
            consensus_methodology_urn="urn:karsa:consensus:s1",
            consensus_policy_hash="c" * 64,
            input_review_record_urns=[r1.record_urn, r2.record_urn, r3.record_urn],
            failure_classifications=[fc1, fc2, fc3],
            success_classifications=[sc1, sc2, sc3],
            recommendations=[rec1, rec2, rec3]
        )
        conn.commit()

        assert pm.failure_classification.thesis_error is True
        assert pm.failure_classification.execution_error is True
        assert pm.recommendation.recommendation_code == "THESIS_REVIEW_REQUIRED"

        # 2. Shuffled Order Independence Check
        # Verify that ordering permutations A,B,C and C,B,A produce identical consensus outputs
        fc_abc, sc_abc, rec_abc = solver.solve_consensus(
            records=[r1, r2, r3],
            failure_classifications=[fc1, fc2, fc3],
            success_classifications=[sc1, sc2, sc3],
            recommendations=[rec1, rec2, rec3]
        )

        fc_cba, sc_cba, rec_cba = solver.solve_consensus(
            records=[r3, r2, r1],
            failure_classifications=[fc3, fc2, fc1],
            success_classifications=[sc3, sc2, sc1],
            recommendations=[rec3, rec2, rec1]
        )

        assert fc_abc.thesis_error == fc_cba.thesis_error
        assert fc_abc.execution_error == fc_cba.execution_error
        assert fc_abc.timing_error == fc_cba.timing_error
        assert fc_abc.sizing_error == fc_cba.sizing_error
        assert fc_abc.calibration_error == fc_cba.calibration_error
        
        assert sc_abc.alpha_generation == sc_cba.alpha_generation
        assert sc_abc.execution_efficiency == sc_cba.execution_efficiency
        assert sc_abc.risk_mitigation == sc_cba.risk_mitigation

        assert rec_abc.recommendation_code == rec_cba.recommendation_code
        assert rec_abc.recommendation_category == rec_cba.recommendation_category
        assert rec_abc.recommendation_severity == rec_cba.recommendation_severity
        assert sorted(rec_abc.thesis_refinement_actions) == sorted(rec_cba.thesis_refinement_actions)

        # 3. Tie resolution check (weaker first, stronger second)
        r_tie1 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w1")
        r_tie2 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w2")
        rec_t1 = ImprovementRecommendation("EXECUTION_WARNING", "e", "MEDIUM")
        rec_t2 = ImprovementRecommendation("THESIS_SUSPEND_RECOMMENDED", "t", "CRITICAL")
        
        _, _, rec_resolved = solver.solve_consensus(
            records=[r_tie1, r_tie2],
            failure_classifications=[fc1, fc2],
            success_classifications=[sc1, sc2],
            recommendations=[rec_t1, rec_t2]
        )
        assert rec_resolved.recommendation_code == "THESIS_SUSPEND_RECOMMENDED"


def test_postgres_not_found_cases(clean_db):
    with clean_db.connection() as conn:
        sess_repo = PostgresReviewSessionRepository(conn)
        record_repo = PostgresReviewRecordRepository(conn)
        pm_repo = PostgresPostMortemRecordRepository(conn)
        
        assert sess_repo.find_by_id("00000000-0000-0000-0000-000000000000") is None
        assert sess_repo.find_by_urn("urn:karsa:review:session:non-existent") is None
        
        assert record_repo.find_by_id("00000000-0000-0000-0000-000000000000") is None
        assert record_repo.find_by_urn("urn:karsa:review:record:non-existent") is None
        assert record_repo.find_review_lineage("urn:karsa:review:record:non-existent") == []
        
        assert pm_repo.find_by_id("00000000-0000-0000-0000-000000000000") is None
        assert pm_repo.find_by_urn("urn:karsa:postmortem:record:non-existent") is None
        assert pm_repo.find_postmortem_lineage("urn:karsa:postmortem:record:non-existent") == []


def test_postgres_review_record_supersede_and_save(clean_db):
    with clean_db.connection() as conn:
        sess_repo = PostgresReviewSessionRepository(conn)
        record_repo = PostgresReviewRecordRepository(conn)
        
        sess = make_session(status="CONDUCTING")
        sess_repo.save(sess)
        
        rec = make_record(sess.session_urn)
        record_repo.save(rec)
        conn.commit()
        
        rec.supersede(next_version=2)
        record_repo.save(rec)
        conn.commit()
        
        fetched = record_repo.find_by_id(rec.record_id)
        assert fetched.is_active is False
        assert fetched.superseded_by_version == 2


def test_postgres_cursor_pagination(clean_db):
    with clean_db.connection() as conn:
        sess_repo = PostgresReviewSessionRepository(conn)
        record_repo = PostgresReviewRecordRepository(conn)
        pm_repo = PostgresPostMortemRecordRepository(conn)
        
        sess = make_session(status="CONDUCTING")
        sess_repo.save(sess)
        
        r1 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w1")
        r2 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w1")
        
        sorted_recs = sorted([r1, r2], key=lambda x: x.record_urn)
        for r in sorted_recs:
            record_repo.save(r)
            
        pm1 = make_postmortem(sess.session_urn)
        pm2 = make_postmortem(sess.session_urn)
        sorted_pms = sorted([pm1, pm2], key=lambda x: x.postmortem_urn)
        for pm in sorted_pms:
            pm_repo.save(pm)
            
        conn.commit()
        
        # 1. find_active_by_worker with cursor
        p1_worker = record_repo.find_active_by_worker("urn:karsa:worker:w1", limit=1)
        assert len(p1_worker) == 1
        assert p1_worker[0].record_urn == sorted_recs[0].record_urn
        
        p2_worker = record_repo.find_active_by_worker("urn:karsa:worker:w1", limit=1, cursor=sorted_recs[0].record_urn)
        assert len(p2_worker) == 1
        assert p2_worker[0].record_urn == sorted_recs[1].record_urn
        
        # 2. find_by_session_paginated with cursor (records)
        p1_session = record_repo.find_by_session_paginated(sess.session_urn, limit=1)
        assert len(p1_session) == 1
        assert p1_session[0].record_urn == sorted_recs[0].record_urn
        
        p2_session = record_repo.find_by_session_paginated(sess.session_urn, limit=1, cursor=sorted_recs[0].record_urn)
        assert len(p2_session) == 1
        assert p2_session[0].record_urn == sorted_recs[1].record_urn
        
        # 3. find_by_session_paginated with cursor (postmortems)
        pm_p1 = pm_repo.find_by_session_paginated(sess.session_urn, limit=1)
        assert len(pm_p1) == 1
        assert pm_p1[0].postmortem_urn == sorted_pms[0].postmortem_urn
        
        pm_p2 = pm_repo.find_by_session_paginated(sess.session_urn, limit=1, cursor=sorted_pms[0].postmortem_urn)
        assert len(pm_p2) == 1
        assert pm_p2[0].postmortem_urn == sorted_pms[1].postmortem_urn


def test_consensus_replay_success(clean_db):
    with clean_db.connection() as conn:
        sess_repo = PostgresReviewSessionRepository(conn)
        record_repo = PostgresReviewRecordRepository(conn)
        pm_repo = PostgresPostMortemRecordRepository(conn)

        solver = ConsensusSolver()
        pm_service = PostMortemService(pm_repo, record_repo, solver)

        sess = make_session(status="CONDUCTING")
        sess_repo.save(sess)

        r1 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w1")
        r2 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w2")
        record_repo.save(r1)
        record_repo.save(r2)
        conn.commit()

        fc1 = FailureClassification(True, False, False, False, False)
        fc2 = FailureClassification(True, True, False, False, False)
        sc1 = SuccessClassification(True, False, True)
        sc2 = SuccessClassification(True, True, False)
        rec1 = ImprovementRecommendation("THESIS_REVIEW_REQUIRED", "t", "HIGH")
        rec2 = ImprovementRecommendation("EXECUTION_WARNING", "e", "MEDIUM")

        pm = pm_service.finalize_postmortem(
            postmortem_id=str(uuid.uuid4()),
            postmortem_urn=f"urn:karsa:postmortem:record:{str(uuid.uuid4())}",
            session_urn=sess.session_urn,
            decision_id="dec-1",
            consensus_methodology_urn="urn:karsa:consensus:s1",
            consensus_policy_hash="c" * 64,
            input_review_record_urns=[r1.record_urn, r2.record_urn],
            failure_classifications=[fc1, fc2],
            success_classifications=[sc1, sc2],
            recommendations=[rec1, rec2]
        )
        conn.commit()

        loaded_pm = pm_repo.find_by_id(pm.postmortem_id)
        assert loaded_pm is not None

        # Re-resolve inputs and run solver
        resolved_records = []
        for urn in loaded_pm.input_review_record_urns:
            rec = record_repo.find_by_urn(urn)
            assert rec is not None
            resolved_records.append(rec)

        fc_replayed, sc_replayed, rec_replayed = solver.solve_consensus(
            records=resolved_records,
            failure_classifications=[fc1, fc2],
            success_classifications=[sc1, sc2],
            recommendations=[rec1, rec2]
        )

        assert fc_replayed.thesis_error == loaded_pm.failure_classification.thesis_error
        assert fc_replayed.execution_error == loaded_pm.failure_classification.execution_error
        assert sc_replayed.alpha_generation == loaded_pm.success_classification.alpha_generation
        assert rec_replayed.recommendation_code == loaded_pm.recommendation.recommendation_code


def test_consensus_methodology_drift_detection(clean_db):
    with clean_db.connection() as conn:
        sess_repo = PostgresReviewSessionRepository(conn)
        record_repo = PostgresReviewRecordRepository(conn)
        pm_repo = PostgresPostMortemRecordRepository(conn)

        sess = make_session(status="CONDUCTING")
        sess_repo.save(sess)

        r1 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w1")
        record_repo.save(r1)
        
        fc = FailureClassification(True, False, False, False, False)
        sc = SuccessClassification(True, False, True)
        rec = ImprovementRecommendation("THESIS_REVIEW_REQUIRED", "t", "HIGH")

        solver = ConsensusSolver()
        pm_service = PostMortemService(pm_repo, record_repo, solver)

        pm = pm_service.finalize_postmortem(
            postmortem_id=str(uuid.uuid4()),
            postmortem_urn=f"urn:karsa:postmortem:record:{str(uuid.uuid4())}",
            session_urn=sess.session_urn,
            decision_id="dec-1",
            consensus_methodology_urn="urn:karsa:consensus:s1",
            consensus_policy_hash="c" * 64,
            input_review_record_urns=[r1.record_urn],
            failure_classifications=[fc],
            success_classifications=[sc],
            recommendations=[rec]
        )
        conn.commit()

        # Replay validation function to check methodology/policy drift
        def verify_consensus_replay_methodology(pm_rec: PostMortemRecord, current_urn: str, current_hash: str):
            if pm_rec.consensus_methodology_urn != current_urn:
                raise MethodologyDriftException(
                    f"Consensus methodology drift detected! Pinned URN: {pm_rec.consensus_methodology_urn}, Current: {current_urn}"
                )
            if pm_rec.consensus_policy_hash != current_hash:
                raise MethodologyDriftException(
                    f"Consensus policy hash drift detected! Pinned: {pm_rec.consensus_policy_hash}, Current: {current_hash}"
                )

        loaded_pm = pm_repo.find_by_id(pm.postmortem_id)
        assert loaded_pm is not None

        # Verify no drift initially
        verify_consensus_replay_methodology(loaded_pm, "urn:karsa:consensus:s1", "c" * 64)

        # Verify drift detection raises MethodologyDriftException for drifted URN
        with pytest.raises(MethodologyDriftException, match="Consensus methodology drift detected"):
            verify_consensus_replay_methodology(loaded_pm, "urn:karsa:consensus:s2", "c" * 64)

        # Verify drift detection raises MethodologyDriftException for drifted hash
        with pytest.raises(MethodologyDriftException, match="Consensus policy hash drift detected"):
            verify_consensus_replay_methodology(loaded_pm, "urn:karsa:consensus:s1", "d" * 64)


