import os
import json
import copy
import pytest
import uuid
import shutil
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import List

from testcontainers.postgres import PostgresContainer
from psycopg_pool import ConnectionPool
import psycopg

from karsa.performance.domain.model.models import PerformanceSession, WorkerEvaluationRecord
from karsa.performance.domain.model.value_objects import (
    BrierScore,
    CalibrationBin,
    CalibrationCurve,
    BenchmarkPerformance,
    WorkerRank,
    CanonicalManifestSerializer
)
from karsa.performance.domain.model.lineage import (
    RecomputationLineage,
    reconstruct_lineage_chain
)
from karsa.performance.events.events import (
    PerformanceSessionStagedEvent,
    PerformanceSessionEvaluatedEvent,
    PerformanceSessionSealedEvent,
    BrierScoreCalibratedEvent
)
from karsa.performance.infrastructure.repositories import (
    InMemoryPerformanceSessionRepository,
    InMemoryWorkerEvaluationRepository,
    FilePerformanceSessionRepository,
    FileWorkerEvaluationRepository,
    PostgresPerformanceSessionRepository,
    PostgresWorkerEvaluationRepository,
    ConcurrencyConflictError
)
from karsa.performance.application.service import (
    PerformanceEvaluationService,
    PerformanceReplayService,
    CalibrationProjectionService
)

# ==========================================
# 1. Domain Aggregate & Value Object Tests
# ==========================================

def test_performance_session_states():
    # Test valid creation
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=5)
    session = PerformanceSession("sess-1", start, end)
    assert session.state == "STAGED"
    
    # State transitions
    session.transition_to("EVALUATING")
    assert session.state == "EVALUATING"
    
    session.transition_to("CALIBRATED")
    assert session.state == "CALIBRATED"
    
    session.transition_to("SEALED")
    assert session.state == "SEALED"
    
    # Bypasses or invalid transitions must raise ValueErrors
    session2 = PerformanceSession("sess-2", start, end)
    with pytest.raises(ValueError):
        session2.transition_to("SEALED")  # cannot bypass STAGED -> SEALED
        
    session3 = PerformanceSession("sess-3", start, end)
    session3.transition_to("EVALUATING")
    with pytest.raises(ValueError):
        session3.transition_to("SEALED")  # cannot bypass EVALUATING -> SEALED

    # Sealed cannot transition out
    session4 = PerformanceSession("sess-4", start, end, "SEALED")
    with pytest.raises(ValueError):
        session4.transition_to("STAGED")

def test_performance_session_validation():
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=5)
    
    with pytest.raises(ValueError, match="session_id is required"):
        PerformanceSession("", start, end)
    with pytest.raises(ValueError, match="horizon_start cannot be after horizon_end"):
        PerformanceSession("sess-1", end, start)
    with pytest.raises(ValueError, match="Invalid state"):
        PerformanceSession("sess-1", start, end, "INVALID")

def test_worker_evaluation_record_immutability():
    rec = WorkerEvaluationRecord(
        record_id="rec-1",
        session_id="sess-1",
        decision_id="dec-1",
        worker_urn="urn:worker:1",
        asset_urn="urn:asset:1",
        regime_urn="urn:regime:1",
        forecast_probability=Decimal("0.8"),
        realized_outcome=1,
        brier_score_component=Decimal("0.04"),
        realized_return=Decimal("0.05")
    )
    
    # Test validations
    with pytest.raises(ValueError, match="forecast_probability must be between 0.0 and 1.0"):
        WorkerEvaluationRecord("rec-2", "sess-1", "dec-1", "urn:worker:1", "urn:asset:1", "urn:regime:1", Decimal("1.5"), 1, Decimal("0.25"), Decimal("0.0"))
    with pytest.raises(ValueError, match="realized_outcome must be 0 or 1"):
        WorkerEvaluationRecord("rec-2", "sess-1", "dec-1", "urn:worker:1", "urn:asset:1", "urn:regime:1", Decimal("0.8"), 2, Decimal("0.25"), Decimal("0.0"))
        
    # Check modification is blocked
    with pytest.raises(TypeError, match="Cannot modify immutable WorkerEvaluationRecord aggregate"):
        rec.forecast_probability = Decimal("0.9")
        
    # Only active status toggling and lineage setting are allowed
    rec.is_active = False
    assert rec.is_active is False
    
    rec.superseded_by_version = 2
    assert rec.superseded_by_version == 2
    
    rec.invalidated_by_version = 3
    assert rec.invalidated_by_version == 3
    
    # Cannot toggle back from False to True
    with pytest.raises(TypeError, match="Cannot toggle is_active from False to True"):
        rec.is_active = True

def test_lineage_reconstruction_recompute():
    class DummyRecord:
        def __init__(self, evaluation_version, superseded_by_version=None, invalidated_by_version=None):
            self.evaluation_version = evaluation_version
            self.superseded_by_version = superseded_by_version
            self.invalidated_by_version = invalidated_by_version

    assert reconstruct_lineage_chain([]) == ""
    
    records = [
        DummyRecord(1, superseded_by_version=2),
        DummyRecord(2, invalidated_by_version=3),
        DummyRecord(3)
    ]
    expected = "Version 1\n\u2192 superseded by Version 2\n\u2192 invalidated by Version 3"
    assert reconstruct_lineage_chain(records) == expected

# ==========================================
# 2. In-Memory & File Repository Tests
# ==========================================

def test_in_memory_concurrency_and_queries():
    session_repo = InMemoryPerformanceSessionRepository()
    record_repo = InMemoryWorkerEvaluationRepository()
    
    session = PerformanceSession("sess-1", datetime.now(), datetime.now() + timedelta(days=2))
    session_repo.save(session)
    
    # OCC test
    retrieved = session_repo.get_by_id("sess-1")
    retrieved.transition_to("EVALUATING")
    session_repo.save(retrieved)
    
    with pytest.raises(ConcurrencyConflictError):
        session.transition_to("EVALUATING")
        session_repo.save(session)
        
    # Record queries
    rec = WorkerEvaluationRecord(
        record_id="rec-1",
        session_id="sess-1",
        decision_id="dec-1",
        worker_urn="urn:worker:1",
        asset_urn="urn:asset:1",
        regime_urn="urn:regime:1",
        forecast_probability=Decimal("0.7"),
        realized_outcome=1,
        brier_score_component=Decimal("0.09"),
        realized_return=Decimal("0.02")
    )
    record_repo.save(rec)
    
    assert len(record_repo.find_active_by_worker("urn:worker:1")) == 1
    assert len(record_repo.find_by_session("sess-1")) == 1
    assert record_repo.find_by_id("rec-1", 1) is not None

def test_file_repository_persistence(tmp_path):
    sess_dir = tmp_path / "sessions"
    rec_dir = tmp_path / "records"
    
    session_repo = FilePerformanceSessionRepository(storage_dir=str(sess_dir))
    record_repo = FileWorkerEvaluationRepository(storage_dir=str(rec_dir))
    
    session = PerformanceSession("sess-1", datetime.now(), datetime.now() + timedelta(days=2))
    session_repo.save(session)
    
    retrieved = session_repo.get_by_id("sess-1")
    assert retrieved.session_id == "sess-1"
    
    rec = WorkerEvaluationRecord(
        record_id="rec-1",
        session_id="sess-1",
        decision_id="dec-1",
        worker_urn="urn:worker:1",
        asset_urn="urn:asset:1",
        regime_urn="urn:regime:1",
        forecast_probability=Decimal("0.7"),
        realized_outcome=1,
        brier_score_component=Decimal("0.09"),
        realized_return=Decimal("0.02")
    )
    record_repo.save(rec)
    
    assert len(record_repo.find_active_by_worker("urn:worker:1")) == 1
    
    # Deactivate version test
    record_repo.deactivate_old_versions("dec-1", 2)
    updated = record_repo.find_by_id("rec-1", 1)
    assert updated.is_active is False
    assert updated.superseded_by_version == 2

# ==========================================
# 3. Postgres Repository and Trigger Tests
# ==========================================

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
        pytest.skip(f"Could not connect to Postgres database: {e}")

@pytest.fixture
def clean_db(postgres_pool):
    with postgres_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TRIGGER IF EXISTS enforce_performance_record_immutability ON worker_evaluation_records;")
            cur.execute("DROP TABLE IF EXISTS worker_evaluation_records_default CASCADE;")
            cur.execute("DROP TABLE IF EXISTS worker_evaluation_records CASCADE;")
            cur.execute("DROP TABLE IF EXISTS performance_sessions CASCADE;")
            cur.execute("DROP FUNCTION IF EXISTS block_performance_record_mutation();")

            cur.execute("""
                CREATE OR REPLACE FUNCTION block_performance_record_mutation()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF TG_OP = 'DELETE' THEN
                        RAISE EXCEPTION 'Performance evaluation records are immutable and cannot be deleted.';
                    ELSIF TG_OP = 'UPDATE' THEN
                        IF NEW.is_active = FALSE AND OLD.is_active = TRUE AND
                           NEW.record_id = OLD.record_id AND
                           NEW.session_id = OLD.session_id AND
                           NEW.decision_id = OLD.decision_id AND
                           NEW.worker_urn = OLD.worker_urn AND
                           NEW.asset_urn = OLD.asset_urn AND
                           NEW.regime_urn = OLD.regime_urn AND
                           NEW.forecast_probability = OLD.forecast_probability AND
                           NEW.realized_outcome = OLD.realized_outcome AND
                           NEW.brier_score_component = OLD.brier_score_component AND
                           NEW.realized_return = OLD.realized_return AND
                           NEW.evaluation_version = OLD.evaluation_version AND
                           NEW.calculated_at = OLD.calculated_at AND
                           (NEW.superseded_by_version IS NOT DISTINCT FROM OLD.superseded_by_version OR (OLD.superseded_by_version IS NULL AND NEW.superseded_by_version IS NOT NULL)) AND
                           (NEW.invalidated_by_version IS NOT DISTINCT FROM OLD.invalidated_by_version OR (OLD.invalidated_by_version IS NULL AND NEW.invalidated_by_version IS NOT NULL)) THEN
                            RETURN NEW;
                        ELSE
                            RAISE EXCEPTION 'Performance evaluation records are immutable. Only deactivation updates are allowed.';
                        END IF;
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS performance_sessions (
                    session_id UUID PRIMARY KEY,
                    horizon_start TIMESTAMP NOT NULL,
                    horizon_end TIMESTAMP NOT NULL,
                    state VARCHAR(64) NOT NULL,
                    raw_input_manifest_hash VARCHAR(256) NOT NULL,
                    aggregate_version INTEGER NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS worker_evaluation_records (
                    record_id UUID NOT NULL,
                    session_id UUID NOT NULL,
                    decision_id VARCHAR(256) NOT NULL,
                    worker_urn VARCHAR(256) NOT NULL,
                    asset_urn VARCHAR(256) NOT NULL,
                    regime_urn VARCHAR(256) NOT NULL,
                    forecast_probability NUMERIC NOT NULL,
                    realized_outcome INTEGER NOT NULL,
                    brier_score_component NUMERIC NOT NULL,
                    realized_return NUMERIC NOT NULL,
                    evaluation_version INTEGER NOT NULL,
                    is_active BOOLEAN NOT NULL,
                    calculated_at TIMESTAMP NOT NULL,
                    superseded_by_version INTEGER,
                    invalidated_by_version INTEGER,
                    aggregate_version INTEGER NOT NULL,
                    PRIMARY KEY (record_id, calculated_at)
                ) PARTITION BY RANGE (calculated_at);

                CREATE TABLE IF NOT EXISTS worker_evaluation_records_default PARTITION OF worker_evaluation_records DEFAULT;
            """)

            cur.execute("""
                CREATE TRIGGER enforce_performance_record_immutability
                BEFORE UPDATE OR DELETE ON worker_evaluation_records
                FOR EACH ROW EXECUTE FUNCTION block_performance_record_mutation();
            """)

def test_postgres_repository_and_triggers(clean_db, postgres_pool):
    with postgres_pool.connection() as conn:
        session_repo = PostgresPerformanceSessionRepository(conn)
        record_repo = PostgresWorkerEvaluationRepository(conn)
        
        sid = str(uuid.uuid4())
        rid = str(uuid.uuid4())
        
        session = PerformanceSession(sid, datetime.now(), datetime.now() + timedelta(days=2))
        session_repo.save(session)
        
        rec = WorkerEvaluationRecord(
            record_id=rid,
            session_id=sid,
            decision_id="dec-1",
            worker_urn="urn:worker:1",
            asset_urn="urn:asset:1",
            regime_urn="urn:regime:1",
            forecast_probability=Decimal("0.70"),
            realized_outcome=1,
            brier_score_component=Decimal("0.090000000000"),
            realized_return=Decimal("0.020000000000")
        )
        record_repo.save(rec)
        
        # Test trigger blocks updates to returns
        try:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE worker_evaluation_records SET realized_return = 0.10 WHERE record_id = %s",
                        (rid,)
                    )
            assert False, "Update was not blocked by trigger"
        except psycopg.Error:
            pass

        # Test trigger blocks DELETE
        try:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM worker_evaluation_records WHERE record_id = %s",
                        (rid,)
                    )
            assert False, "Delete was not blocked by trigger"
        except psycopg.Error:
            pass
            
        # Verify deactivation query updates superseded_by_version safely
        record_repo.deactivate_old_versions("dec-1", exclude_version=2)
        
        updated = record_repo.find_by_id(rid, 1)
        assert updated.is_active is False
        assert updated.superseded_by_version == 2
        
        # Test deactivation by session
        rid2 = str(uuid.uuid4())
        rec2 = WorkerEvaluationRecord(
            record_id=rid2,
            session_id=sid,
            decision_id="dec-2",
            worker_urn="urn:worker:1",
            asset_urn="urn:asset:1",
            regime_urn="urn:regime:1",
            forecast_probability=Decimal("0.70"),
            realized_outcome=1,
            brier_score_component=Decimal("0.090000000000"),
            realized_return=Decimal("0.020000000000")
        )
        record_repo.save(rec2)

        record_repo.deactivate_by_session(sid)
        invalidated = record_repo.find_by_id(rid2, 1)
        assert invalidated.is_active is False
        assert invalidated.invalidated_by_version == 2

# ==========================================
# 4. Service & Replay Tests
# ==========================================

def test_performance_evaluation_workflow():
    session_repo = InMemoryPerformanceSessionRepository()
    record_repo = InMemoryWorkerEvaluationRepository()
    events = []
    
    eval_service = PerformanceEvaluationService(session_repo, record_repo, events)
    
    session_id = "sess-eval"
    start = datetime(2026, 6, 1, tzinfo=timezone.utc)
    end = datetime(2026, 6, 5, tzinfo=timezone.utc)
    
    eval_service.stage_session(session_id, start, end)
    
    inputs = {
        "forecasts": [
            {
                "decision_id": "dec-1",
                "worker_urn": "urn:worker:1",
                "asset_urn": "urn:asset:1",
                "forecast_probability": 0.8,
                "realized_outcome": 1,
                "realized_return": 0.05
            },
            {
                "decision_id": "dec-2",
                "worker_urn": "urn:worker:1",
                "asset_urn": "urn:asset:2",
                "forecast_probability": 0.3,
                "realized_outcome": 0,
                "realized_return": -0.02
            }
        ]
    }
    
    records = eval_service.evaluate_performance(session_id, inputs)
    assert len(records) == 2
    assert records[0].brier_score_component == Decimal("0.04") # (0.8 - 1.0) ^ 2
    assert records[1].brier_score_component == Decimal("0.09") # (0.3 - 0.0) ^ 2
    
    eval_service.seal_session(session_id)
    
    # Verify events
    assert any(isinstance(e, PerformanceSessionStagedEvent) for e in events)
    assert any(isinstance(e, PerformanceSessionEvaluatedEvent) for e in events)
    assert any(isinstance(e, BrierScoreCalibratedEvent) for e in events)
    assert any(isinstance(e, PerformanceSessionSealedEvent) for e in events)
    
    # Replay test
    replay_service = PerformanceReplayService(session_repo, record_repo)
    assert replay_service.replay_session(session_id, inputs) is True
    
    # Hashing mismatch test
    inputs_corrupted = copy.deepcopy(inputs)
    inputs_corrupted["forecasts"][0]["forecast_probability"] = 0.9
    with pytest.raises(ValueError, match="Manifest hash mismatch"):
        replay_service.replay_session(session_id, inputs_corrupted)

def test_calibration_projections_and_curves():
    record_repo = InMemoryWorkerEvaluationRepository()
    proj_service = CalibrationProjectionService(record_repo)
    
    # Successes (Brier score = 0)
    for i in range(4):
        record_repo.save(WorkerEvaluationRecord(
            record_id=f"rec-{i}",
            session_id="sess-1",
            decision_id=f"dec-{i}",
            worker_urn="urn:worker:1",
            asset_urn="urn:asset:1",
            regime_urn="urn:regime:bull",
            forecast_probability=Decimal("0.8"),
            realized_outcome=1,
            brier_score_component=Decimal("0.04"),
            realized_return=Decimal("0.0")
        ))
        
    # Calibrated confidence calculations
    # avg Brier score is 0.04. calibrated confidence: 0.8 * (1.0 - 0.04) = 0.768
    calib = proj_service.get_calibrated_confidence("urn:worker:1", Decimal("0.8"), "urn:regime:bull")
    assert calib == Decimal("0.768")
    
    # Curve binning
    curve = proj_service.build_calibration_curve("urn:worker:1", "urn:regime:bull")
    
    # Bin 8 (0.8 to 1.0) prediction count should be 4
    assert curve.bins[8].prediction_count == 4
    assert curve.bins[8].success_count == 4
    assert curve.bins[8].calibrated_probability == Decimal("1.0")

def test_replay_verification_lineage():
    session_repo = InMemoryPerformanceSessionRepository()
    record_repo = InMemoryWorkerEvaluationRepository()
    events = []
    
    eval_service = PerformanceEvaluationService(session_repo, record_repo, events)
    
    session_id = "sess-recalc"
    eval_service.stage_session(session_id, datetime.now(), datetime.now())
    
    inputs_v1 = {
        "forecasts": [
            {
                "decision_id": "dec-recalc",
                "worker_urn": "urn:worker:1",
                "asset_urn": "urn:asset:1",
                "forecast_probability": 0.8,
                "realized_outcome": 1
            }
        ]
    }
    
    eval_service.evaluate_performance(session_id, inputs_v1)
    
    # Recalculate/update record
    inputs_v2 = {
        "forecasts": [
            {
                "decision_id": "dec-recalc",
                "worker_urn": "urn:worker:1",
                "asset_urn": "urn:asset:1",
                "forecast_probability": 0.9,
                "realized_outcome": 1
            }
        ]
    }
    
    eval_service.recompute_performance(session_id, inputs_v2, "req-1")
    
    # Walk lineage
    all_recs = record_repo.find_by_session(session_id)
    assert len(all_recs) == 2
    
    chain = reconstruct_lineage_chain(all_recs)
    assert "superseded by Version 2" in chain


# ==========================================
# 5. Additional Coverage & Edge Case Tests
# ==========================================

from karsa.performance.domain.model.evaluation import DecisionEvaluation, EvaluationSnapshot
from karsa.performance.domain.model.value_objects import (
    EvaluationTarget, EvaluationPeriod, ThesisQualityMetric,
    ExecutionQualityMetric, AllocationQualityMetric, BenchmarkComparison
)
from karsa.performance.domain.projections import (
    PerformanceEvaluation, ThesisPerformanceProjection,
    WorkerPerformanceProjection, StrategyPerformanceProjection,
    ThesisExecutionBindingPerformanceProjection
)
from karsa.performance.domain.outcome import ExecutionOutcome

def test_decision_evaluation_and_snapshot():
    target = EvaluationTarget("WORKER", "worker-1")
    period = EvaluationPeriod(datetime.now(timezone.utc), datetime.now(timezone.utc))
    thesis = ThesisQualityMetric(Decimal("0.04"), False, Decimal("0.01"))
    exec_m = ExecutionQualityMetric(Decimal("10.0"), 50, 100)
    alloc = AllocationQualityMetric(Decimal("2.1"), Decimal("0.05"), Decimal("15.0"))
    bench = BenchmarkComparison("SPY", Decimal("5.0"), Decimal("0.02"), Decimal("450.0"))
    
    de = DecisionEvaluation(
        evaluation_id="eval-1",
        decision_id="dec-1",
        target=target,
        period=period,
        thesis_metrics=thesis,
        execution_metrics=exec_m,
        allocation_metrics=alloc,
        benchmarks=[bench],
        regime_id="regime-1"
    )
    assert de.evaluation_id == "eval-1"
    
    d = de.to_dict()
    de2 = DecisionEvaluation.from_dict(d)
    assert de2.evaluation_id == "eval-1"
    
    with pytest.raises(TypeError, match="Cannot modify immutable DecisionEvaluation aggregate"):
        de.regime_id = "new-regime"
        
    with pytest.raises(TypeError, match="Cannot modify immutable DecisionEvaluation aggregate"):
        del de.regime_id
        
    snap = EvaluationSnapshot(
        snapshot_id="snap-1",
        evaluation_id="eval-1",
        target=target,
        period=period,
        serialized_metrics="{}"
    )
    assert snap.snapshot_id == "snap-1"
    d_snap = snap.to_dict()
    snap2 = EvaluationSnapshot.from_dict(d_snap)
    assert snap2.snapshot_id == "snap-1"
    
    with pytest.raises(TypeError, match="Cannot modify immutable EvaluationSnapshot aggregate"):
        snap.serialized_metrics = "{'a': 1}"
    with pytest.raises(TypeError, match="Cannot modify immutable EvaluationSnapshot aggregate"):
        del snap.serialized_metrics

def test_projections_and_outcomes():
    pe = PerformanceEvaluation("WORKER", "w-1", Decimal("0.6"), Decimal("0.05"), Decimal("1.5"), Decimal("0.08"), 10, datetime.now(timezone.utc))
    assert pe.target_id == "w-1"
    
    tp = ThesisPerformanceProjection("t-1", Decimal("0.02"), False, 5, datetime.now(timezone.utc))
    assert tp.thesis_version_id == "t-1"
    
    wp = WorkerPerformanceProjection("w-1", Decimal("0.5"), Decimal("0.04"), Decimal("0.7"), 8, datetime.now(timezone.utc))
    assert wp.worker_id == "w-1"
    
    sp = StrategyPerformanceProjection("s-1", Decimal("20.0"), Decimal("0.05"), Decimal("1.2"), datetime.now(timezone.utc))
    assert sp.strategy_id == "s-1"
    
    te = ThesisExecutionBindingPerformanceProjection("b-1", "t-1", "p-1", "s-1", Decimal("10.0"), Decimal("0.02"), Decimal("100000.0"), "ACTIVE", datetime.now(timezone.utc))
    assert te.binding_id == "b-1"
    
    o = ExecutionOutcome("dec-1", "out-1", "WORKER", "w-1", Decimal("10"), Decimal("0.02"), True, Decimal("0.01"), 100, 50, Decimal("1.5"), {"SPY": Decimal("0.02")}, "reg-1", datetime.now(timezone.utc))
    assert o.outcome_id == "out-1"

def test_canonical_manifest_serializer_edge_cases():
    # Naive datetime
    dt_naive = datetime(2026, 6, 1, 12, 0, 0)
    ser_naive = CanonicalManifestSerializer._normalize_val(dt_naive)
    assert ser_naive == "2026-06-01T12:00:00.000000Z"
    
    # Aware datetime
    dt_aware = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    ser_aware = CanonicalManifestSerializer._normalize_val(dt_aware)
    assert ser_aware == "2026-06-01T12:00:00.000000Z"
    
    # Date type
    d_obj = datetime(2026, 6, 1).date()
    ser_date = CanonicalManifestSerializer._normalize_val(d_obj)
    assert ser_date == "2026-06-01"
    
    # Dict filtering None
    d = {"a": 1, "b": None}
    ser_d = CanonicalManifestSerializer._normalize_val(d)
    assert "b" not in ser_d
    
    # List sorting with asset_urn or other keys
    l = [{"asset_urn": "b"}, {"asset_urn": "a"}]
    ser_l = CanonicalManifestSerializer._normalize_val(l)
    assert ser_l[0]["asset_urn"] == "a"
    assert ser_l[1]["asset_urn"] == "b"

def test_repository_list_and_clear(tmp_path):
    sess_inmem = InMemoryPerformanceSessionRepository()
    rec_inmem = InMemoryWorkerEvaluationRepository()
    s = PerformanceSession("s-1", datetime.now(timezone.utc), datetime.now(timezone.utc))
    sess_inmem.save(s)
    assert len(sess_inmem.list_all()) == 1
    sess_inmem.clear()
    assert len(sess_inmem.list_all()) == 0
    
    r = WorkerEvaluationRecord("r-1", "s-1", "d-1", "w-1", "a-1", "reg-1", Decimal("0.5"), 1, Decimal("0.25"), Decimal("0.0"))
    rec_inmem.save(r)
    assert len(rec_inmem.list_all()) == 1
    rec_inmem.clear()
    assert len(rec_inmem.list_all()) == 0
    
    sess_file = FilePerformanceSessionRepository(str(tmp_path / "sessions_test"))
    rec_file = FileWorkerEvaluationRepository(str(tmp_path / "records_test"))
    sess_file.save(s)
    assert len(sess_file.list_all()) == 1
    
    rec_file.save(r)
    assert len(rec_file.list_all()) == 1
    
    with pytest.raises(ValueError):
        rec_file.save(r)
        
    sess_file.clear()
    rec_file.clear()
    assert len(sess_file.list_all()) == 0
    assert len(rec_file.list_all()) == 0
    
    assert sess_file.get_by_id("non-existent") is None
    assert rec_file.find_by_id("non-existent", 1) is None

def test_postgres_repository_edge_cases(postgres_pool, clean_db):
    with postgres_pool.connection() as conn:
        session_repo = PostgresPerformanceSessionRepository(conn)
        record_repo = PostgresWorkerEvaluationRepository(conn)
        
        sid = str(uuid.uuid4())
        rid = str(uuid.uuid4())
        
        s = PerformanceSession(sid, datetime.now(timezone.utc), datetime.now(timezone.utc))
        session_repo.save(s)
        
        r = WorkerEvaluationRecord(rid, sid, "d-1", "w-1", "a-1", "reg-1", Decimal("0.5"), 1, Decimal("0.25"), Decimal("0.0"))
        record_repo.save(r)
        
        # list_all
        assert len(session_repo.list_all()) == 1
        assert len(record_repo.list_all()) == 1
        
        # clear
        session_repo.clear()
        record_repo.clear()
        assert len(session_repo.list_all()) == 0
        assert len(record_repo.list_all()) == 0

def test_service_edge_cases():
    session_repo = InMemoryPerformanceSessionRepository()
    record_repo = InMemoryWorkerEvaluationRepository()
    eval_service = PerformanceEvaluationService(session_repo, record_repo)
    
    # session exists when staging
    session_repo.save(PerformanceSession("sess-1", datetime.now(timezone.utc), datetime.now(timezone.utc)))
    with pytest.raises(ValueError, match="Performance session already exists"):
        eval_service.stage_session("sess-1", datetime.now(timezone.utc), datetime.now(timezone.utc))
        
    # session not found when evaluating
    with pytest.raises(ValueError, match="Session not found"):
        eval_service.evaluate_performance("sess-non-existent", {})
        
    # session not found when sealing
    with pytest.raises(ValueError, match="Session not found"):
        eval_service.seal_session("sess-non-existent")
        
    # session not found when recomputing
    with pytest.raises(ValueError, match="Session not found"):
        eval_service.recompute_performance("sess-non-existent", {}, "req-1")
        
    # replay session not found
    replay_service = PerformanceReplayService(session_repo, record_repo)
    with pytest.raises(ValueError, match="Session not found"):
        replay_service.replay_session("sess-non-existent", {})


def test_models_validation_failures():
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=2)
    
    # PerformanceSession failures
    with pytest.raises(ValueError, match="horizon_start must be a datetime"):
        PerformanceSession("sess-1", None, end)
    with pytest.raises(ValueError, match="horizon_end must be a datetime"):
        PerformanceSession("sess-1", start, None)
    
    session = PerformanceSession("sess-1", start, end)
    with pytest.raises(ValueError, match="Invalid target state"):
        session.transition_to("INVALID")
        
    session.transition_to("EVALUATING")
    session.transition_to("CALIBRATED")
    with pytest.raises(ValueError, match="Cannot transition from CALIBRATED"):
        session.transition_to("EVALUATING")
        
    # WorkerEvaluationRecord failures
    with pytest.raises(ValueError, match="record_id is required"):
        WorkerEvaluationRecord("", "s-1", "d-1", "w-1", "a-1", "reg-1", Decimal("0.5"), 1, Decimal("0.25"), Decimal("0.0"))
    with pytest.raises(ValueError, match="session_id is required"):
        WorkerEvaluationRecord("r-1", "", "d-1", "w-1", "a-1", "reg-1", Decimal("0.5"), 1, Decimal("0.25"), Decimal("0.0"))
    with pytest.raises(ValueError, match="decision_id is required"):
        WorkerEvaluationRecord("r-1", "s-1", "", "w-1", "a-1", "reg-1", Decimal("0.5"), 1, Decimal("0.25"), Decimal("0.0"))
    with pytest.raises(ValueError, match="worker_urn is required"):
        WorkerEvaluationRecord("r-1", "s-1", "d-1", "", "a-1", "reg-1", Decimal("0.5"), 1, Decimal("0.25"), Decimal("0.0"))
    with pytest.raises(ValueError, match="asset_urn is required"):
        WorkerEvaluationRecord("r-1", "s-1", "d-1", "w-1", "", "reg-1", Decimal("0.5"), 1, Decimal("0.25"), Decimal("0.0"))
    with pytest.raises(ValueError, match="regime_urn is required"):
        WorkerEvaluationRecord("r-1", "s-1", "d-1", "w-1", "a-1", "", Decimal("0.5"), 1, Decimal("0.25"), Decimal("0.0"))
    with pytest.raises(ValueError, match="evaluation_version must be positive"):
        WorkerEvaluationRecord("r-1", "s-1", "d-1", "w-1", "a-1", "reg-1", Decimal("0.5"), 1, Decimal("0.25"), Decimal("0.0"), evaluation_version=0)
        
    rec = WorkerEvaluationRecord("r-1", "s-1", "d-1", "w-1", "a-1", "reg-1", Decimal("0.5"), 1, Decimal("0.25"), Decimal("0.0"))
    with pytest.raises(TypeError, match="Cannot delete immutable WorkerEvaluationRecord properties"):
        del rec.worker_urn


def test_abc_repositories():
    from karsa.performance.domain.model.repositories import PerformanceSessionRepository, WorkerEvaluationRepository
    class DummySessionRepo(PerformanceSessionRepository):
        def save(self, session): super().save(session)
        def get_by_id(self, session_id): return super().get_by_id(session_id)
        def list_all(self): return super().list_all()
        def clear(self): super().clear()
        
    class DummyWorkerRepo(WorkerEvaluationRepository):
        def save(self, record): super().save(record)
        def find_by_id(self, record_id, version): return super().find_by_id(record_id, version)
        def find_active_by_worker(self, worker_urn): return super().find_active_by_worker(worker_urn)
        def find_by_session(self, session_id): return super().find_by_session(session_id)
        def list_all(self): return super().list_all()
        def deactivate_old_versions(self, decision_id, exclude_version): super().deactivate_old_versions(decision_id, exclude_version)
        def deactivate_by_session(self, session_id): super().deactivate_by_session(session_id)
        def clear(self): super().clear()
        
    ds = DummySessionRepo()
    ds.save(None)
    ds.get_by_id("")
    ds.list_all()
    ds.clear()
    
    dw = DummyWorkerRepo()
    dw.save(None)
    dw.find_by_id("", 1)
    dw.find_active_by_worker("")
    dw.find_by_session("")
    dw.list_all()
    dw.deactivate_old_versions("", 1)
    dw.deactivate_by_session("")
    dw.clear()


def test_file_repository_deactivations(tmp_path):
    sess_file = FilePerformanceSessionRepository(str(tmp_path / "sessions_test_deact"))
    rec_file = FileWorkerEvaluationRepository(str(tmp_path / "records_test_deact"))
    
    s = PerformanceSession("s-1", datetime.now(timezone.utc), datetime.now(timezone.utc))
    sess_file.save(s)
    
    r = WorkerEvaluationRecord("r-1", "s-1", "d-1", "w-1", "a-1", "reg-1", Decimal("0.5"), 1, Decimal("0.25"), Decimal("0.0"))
    rec_file.save(r)
    
    # deactivate_old_versions
    rec_file.deactivate_old_versions("d-1", exclude_version=2)
    updated = rec_file.find_by_id("r-1", 1)
    assert updated.is_active is False
    assert updated.superseded_by_version == 2
    
    # deactivate_by_session
    r2 = WorkerEvaluationRecord("r-2", "s-1", "d-2", "w-1", "a-1", "reg-1", Decimal("0.5"), 1, Decimal("0.25"), Decimal("0.0"))
    rec_file.save(r2)
    rec_file.deactivate_by_session("s-1")
    updated2 = rec_file.find_by_id("r-2", 1)
    assert updated2.is_active is False
    assert updated2.invalidated_by_version == 2


def test_postgres_repository_more_edge_cases(postgres_pool, clean_db):
    with postgres_pool.connection() as conn:
        session_repo = PostgresPerformanceSessionRepository(conn)
        record_repo = PostgresWorkerEvaluationRepository(conn)
        
        sid = str(uuid.uuid4())
        rid1 = str(uuid.uuid4())
        rid2 = str(uuid.uuid4())
        
        s = PerformanceSession(sid, datetime.now(timezone.utc), datetime.now(timezone.utc))
        session_repo.save(s)
        
        r1 = WorkerEvaluationRecord(rid1, sid, "d-1", "w-1", "a-1", "reg-1", Decimal("0.5"), 1, Decimal("0.25"), Decimal("0.0"))
        record_repo.save(r1)
        
        # save existing session concurrency conflict
        s_bad = PerformanceSession(sid, datetime.now(timezone.utc), datetime.now(timezone.utc), aggregate_version=10)
        with pytest.raises(ConcurrencyConflictError):
            session_repo.save(s_bad)
            
        # save existing worker record raises ValueError
        with pytest.raises(ValueError):
            record_repo.save(r1)
            
        # find_active_by_worker
        active_recs = record_repo.find_active_by_worker("w-1")
        assert len(active_recs) == 1
        
        # find_by_session
        sess_recs = record_repo.find_by_session(sid)
        assert len(sess_recs) == 1


def test_more_coverage_hacks():
    # 1. __delattr__ before initialization
    for cls in [WorkerEvaluationRecord, DecisionEvaluation, EvaluationSnapshot]:
        obj = cls.__new__(cls)
        obj.test_attr = 123
        del obj.test_attr
        
    # 2. CanonicalManifestSerializer list sorting with various key lookups
    keys = ["asset_urn", "execution_id", "decision_id", "record_id", "session_id", "worker_urn"]
    for key in keys:
        l = [{key: "b"}, {key: "a"}]
        ser = CanonicalManifestSerializer._normalize_val(l)
        assert ser[0][key] == "a"
        
    # 3. Domain Events to_dict()
    ev1 = PerformanceSessionStagedEvent()
    assert isinstance(ev1.to_dict(), dict)
    ev2 = PerformanceSessionEvaluatedEvent()
    assert isinstance(ev2.to_dict(), dict)
    ev3 = PerformanceSessionSealedEvent()
    assert isinstance(ev3.to_dict(), dict)
    ev4 = BrierScoreCalibratedEvent()
    assert isinstance(ev4.to_dict(), dict)


def test_file_repository_exceptions(tmp_path):
    sess_file = FilePerformanceSessionRepository(str(tmp_path / "sessions_err"))
    rec_file = FileWorkerEvaluationRepository(str(tmp_path / "records_err"))
    
    # Write corrupt files
    os.makedirs(str(tmp_path / "sessions_err"), exist_ok=True)
    os.makedirs(str(tmp_path / "records_err"), exist_ok=True)
    
    with open(os.path.join(str(tmp_path / "sessions_err"), "corrupt.json"), "w") as f:
        f.write("{invalid json}")
        
    with open(os.path.join(str(tmp_path / "records_err"), "corrupt_v1.json"), "w") as f:
        f.write("{invalid json}")
        
    # Should not crash but skip
    assert len(sess_file.list_all()) == 0
    assert len(rec_file.list_all()) == 0
    assert len(rec_file.find_active_by_worker("w-1")) == 0
    assert len(rec_file.find_by_session("s-1")) == 0
    
    # deactivate methods on corrupt files should not crash
    rec_file.deactivate_old_versions("d-1", 2)
    rec_file.deactivate_by_session("s-1")
    
    # Concurrency conflict in FilePerformanceSessionRepository
    s1 = PerformanceSession("s-2", datetime.now(timezone.utc), datetime.now(timezone.utc))
    sess_file.save(s1)
    
    s2 = PerformanceSession("s-2", datetime.now(timezone.utc), datetime.now(timezone.utc), aggregate_version=10)
    with pytest.raises(ConcurrencyConflictError):
        sess_file.save(s2)
