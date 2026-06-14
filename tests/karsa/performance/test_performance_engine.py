import os
import json
import pytest
import shutil
from decimal import Decimal
from datetime import datetime, timezone
from typing import List

from karsa.performance import (
    DecisionEvaluation,
    EvaluationSnapshot,
    EvaluationTarget,
    EvaluationPeriod,
    ThesisQualityMetric,
    ExecutionQualityMetric,
    AllocationQualityMetric,
    BenchmarkComparison,
    CalibrationBin,
    ConfidenceCalibration,
    DecisionEvaluationRepository,
    EvaluationSnapshotRepository,
    PerformanceEvaluation,
    ThesisPerformanceProjection,
    WorkerPerformanceProjection,
    StrategyPerformanceProjection,
    ThesisExecutionBindingPerformanceProjection,
    ExecutionOutcome,
    DecisionEvaluatedEvent,
    EvaluationSnapshotCreatedEvent,
    PerformanceProjectionUpdatedEvent,
    InMemoryDecisionEvaluationRepository,
    InMemoryEvaluationSnapshotRepository,
    FileDecisionEvaluationRepository,
    FileEvaluationSnapshotRepository,
    ConcurrencyConflictError,
    EvaluationService,
    ProjectionService,
    CalibrationService
)

# Helpers to build mock objects
def create_mock_outcome(decision_id: str, is_success: bool = True, regime_id: str = "BULL") -> ExecutionOutcome:
    return ExecutionOutcome(
        decision_id=decision_id,
        outcome_id=f"out-{decision_id}",
        target_type="WORKER",
        target_id="worker-1",
        actual_return_bps=Decimal("150.0"),
        drawdown_pct=Decimal("0.05"),
        is_success=is_success,
        parameter_deviation=Decimal("0.12"),
        latency_ms=120,
        token_count=1000,
        slippage_bps=Decimal("5.5"),
        benchmark_returns={"SPY": Decimal("100.0")},
        regime_id=regime_id,
        resolved_at=datetime.now(timezone.utc)
    )

# 1. DecisionEvaluation lifecycle
def test_decision_evaluation_lifecycle():
    target = EvaluationTarget("WORKER", "worker-1")
    period = EvaluationPeriod(datetime.now(timezone.utc), datetime.now(timezone.utc))
    thesis = ThesisQualityMetric(Decimal("0.04"), False, Decimal("0.1"))
    execution = ExecutionQualityMetric(Decimal("5.0"), 100, 1000)
    allocation = AllocationQualityMetric(Decimal("1.5"), Decimal("0.05"), Decimal("100.0"))
    benchmarks = [BenchmarkComparison("SPY", Decimal("50.0"), Decimal("0.05"), Decimal("4500.0"))]

    eval_obj = DecisionEvaluation(
        evaluation_id="eval-1",
        decision_id="dec-1",
        target=target,
        period=period,
        thesis_metrics=thesis,
        execution_metrics=execution,
        allocation_metrics=allocation,
        benchmarks=benchmarks,
        regime_id="BULL",
        created_at=datetime.now(timezone.utc),
        aggregate_version=1
    )

    # Immutability check
    with pytest.raises(TypeError):
        eval_obj.decision_id = "new-dec"

    with pytest.raises(TypeError):
        eval_obj.regime_id = "BEAR"

    # Serialization check
    d = eval_obj.to_dict()
    assert d["evaluation_id"] == "eval-1"
    assert d["decision_id"] == "dec-1"
    assert d["target"]["target_type"] == "WORKER"
    
    # Deserialization check
    deserialized = DecisionEvaluation.from_dict(d)
    assert deserialized.evaluation_id == "eval-1"
    assert deserialized.decision_id == "dec-1"
    assert deserialized.target.target_type == "WORKER"
    assert deserialized.thesis_metrics.brier_score == Decimal("0.04")
    assert deserialized.benchmarks[0].benchmark_name == "SPY"


# 2. OCC conflict detection
def test_occ_conflict_detection_in_memory():
    repo = InMemoryDecisionEvaluationRepository()
    
    target = EvaluationTarget("WORKER", "worker-1")
    period = EvaluationPeriod(datetime.now(timezone.utc), datetime.now(timezone.utc))
    thesis = ThesisQualityMetric(Decimal("0.04"), False, Decimal("0.1"))
    execution = ExecutionQualityMetric(Decimal("5.0"), 100, 1000)
    allocation = AllocationQualityMetric(Decimal("1.5"), Decimal("0.05"), Decimal("100.0"))
    
    eval_v1 = DecisionEvaluation(
        evaluation_id="eval-1",
        decision_id="dec-1",
        target=target,
        period=period,
        thesis_metrics=thesis,
        execution_metrics=execution,
        allocation_metrics=allocation,
        benchmarks=[],
        regime_id="BULL",
        created_at=datetime.now(timezone.utc),
        aggregate_version=1
    )
    
    repo.save(eval_v1)
    
    # Saving same version should trigger ConcurrencyConflictError
    eval_v1_conflict = DecisionEvaluation(
        evaluation_id="eval-1-conflict",
        decision_id="dec-1",
        target=target,
        period=period,
        thesis_metrics=thesis,
        execution_metrics=execution,
        allocation_metrics=allocation,
        benchmarks=[],
        regime_id="BULL",
        created_at=datetime.now(timezone.utc),
        aggregate_version=1
    )
    with pytest.raises(ConcurrencyConflictError):
        repo.save(eval_v1_conflict)
        
    # Saving version 2 should succeed
    eval_v2 = DecisionEvaluation(
        evaluation_id="eval-1-v2",
        decision_id="dec-1",
        target=target,
        period=period,
        thesis_metrics=thesis,
        execution_metrics=execution,
        allocation_metrics=allocation,
        benchmarks=[],
        regime_id="BULL",
        created_at=datetime.now(timezone.utc),
        aggregate_version=2
    )
    repo.save(eval_v2)
    assert repo.find_by_decision("dec-1").aggregate_version == 2


# 3. EvaluationSnapshot creation
def test_evaluation_snapshot_creation():
    target = EvaluationTarget("WORKER", "worker-1")
    period = EvaluationPeriod(datetime.now(timezone.utc), datetime.now(timezone.utc))
    
    snap = EvaluationSnapshot(
        snapshot_id="snap-1",
        evaluation_id="eval-1",
        target=target,
        period=period,
        serialized_metrics="{}",
        created_at=datetime.now(timezone.utc),
        aggregate_version=1
    )
    
    # Immutability
    with pytest.raises(TypeError):
        snap.serialized_metrics = '{"key": "value"}'
        
    # Serialization
    d = snap.to_dict()
    assert d["snapshot_id"] == "snap-1"
    
    # Deserialization
    deserialized = EvaluationSnapshot.from_dict(d)
    assert deserialized.snapshot_id == "snap-1"
    assert deserialized.serialized_metrics == "{}"


# 4. Replay determinism
def test_replay_determinism():
    # Service instances
    record_repo = InMemoryDecisionEvaluationRepository()
    snapshot_repo = InMemoryEvaluationSnapshotRepository()
    events = []
    proj_service = ProjectionService(record_repo, events)
    eval_service = EvaluationService(record_repo, snapshot_repo, proj_service, events)

    outcome = create_mock_outcome("dec-1")

    # Perform evaluation twice on different services, check for identity of resulting state
    eval1 = eval_service.consume_execution_outcome(outcome)
    
    # Replay outcome: should produce exact same scores and metrics
    # Note: decision_id is unique per repository so we check determinism by comparing properties
    record_repo_2 = InMemoryDecisionEvaluationRepository()
    snapshot_repo_2 = InMemoryEvaluationSnapshotRepository()
    events_2 = []
    proj_service_2 = ProjectionService(record_repo_2, events_2)
    eval_service_2 = EvaluationService(record_repo_2, snapshot_repo_2, proj_service_2, events_2)
    
    eval2 = eval_service_2.consume_execution_outcome(outcome)
    
    assert eval1.thesis_metrics.brier_score == eval2.thesis_metrics.brier_score
    assert eval1.execution_metrics.slippage_bps == eval2.execution_metrics.slippage_bps
    assert eval1.allocation_metrics.sharpe_ratio == eval2.allocation_metrics.sharpe_ratio
    assert eval1.regime_id == eval2.regime_id


# 5. Projection rebuild
def test_projection_rebuild():
    record_repo = InMemoryDecisionEvaluationRepository()
    snapshot_repo = InMemoryEvaluationSnapshotRepository()
    events = []
    proj_service = ProjectionService(record_repo, events)
    eval_service = EvaluationService(record_repo, snapshot_repo, proj_service, events)

    # Ingest some outcomes
    eval_service.consume_execution_outcome(create_mock_outcome("dec-1"))
    eval_service.consume_execution_outcome(create_mock_outcome("dec-2"))

    # Initial projections check
    proj = proj_service.get_worker_projection("worker-1")
    assert proj is not None
    assert proj.total_decisions == 2

    # Rebuild
    proj_service.rebuild_projections()
    
    # Verify projections exist and match
    proj_rebuild = proj_service.get_worker_projection("worker-1")
    assert proj_rebuild is not None
    assert proj_rebuild.total_decisions == 2


# 6. Projection consistency
def test_projection_consistency():
    record_repo = InMemoryDecisionEvaluationRepository()
    snapshot_repo = InMemoryEvaluationSnapshotRepository()
    events = []
    proj_service = ProjectionService(record_repo, events)
    eval_service = EvaluationService(record_repo, snapshot_repo, proj_service, events)

    # Outcome 1: success
    eval_service.consume_execution_outcome(create_mock_outcome("dec-1", is_success=True))
    # Outcome 2: failure
    eval_service.consume_execution_outcome(create_mock_outcome("dec-2", is_success=False))

    # Total 2 decisions, 1 success, hit rate should be 1/2 = 0.5
    proj = proj_service.get_worker_projection("worker-1")
    assert proj.total_decisions == 2
    assert proj.hit_rate == Decimal("0.5")


# 7. Event emission
def test_event_emission():
    record_repo = InMemoryDecisionEvaluationRepository()
    snapshot_repo = InMemoryEvaluationSnapshotRepository()
    events = []
    proj_service = ProjectionService(record_repo, events)
    eval_service = EvaluationService(record_repo, snapshot_repo, proj_service, events)

    eval_service.consume_execution_outcome(create_mock_outcome("dec-1"))

    # Verify events emitted
    assert len(events) > 0
    
    # Find DecisionEvaluatedEvent
    dec_eval_ev = next(e for e in events if isinstance(e, DecisionEvaluatedEvent))
    assert dec_eval_ev.decision_id == "dec-1"
    assert dec_eval_ev.event_version == 1
    
    # Find EvaluationSnapshotCreatedEvent
    snap_ev = next(e for e in events if isinstance(e, EvaluationSnapshotCreatedEvent))
    assert snap_ev.evaluation_id == dec_eval_ev.evaluation_id

    # Test serialization of event
    ev_dict = dec_eval_ev.to_dict()
    assert ev_dict["event_type"] == "DecisionEvaluatedEvent"
    assert ev_dict["decision_id"] == "dec-1"


# 8. Calibration calculations
def test_calibration_calculations():
    record_repo = InMemoryDecisionEvaluationRepository()
    calibration_service = CalibrationService(record_repo)
    
    # Setup evaluations with specific parameter_deviations as "stated_confidence" simulation
    target = EvaluationTarget("WORKER", "worker-1")
    period = EvaluationPeriod(datetime.now(timezone.utc), datetime.now(timezone.utc))
    execution = ExecutionQualityMetric(Decimal("5.0"), 100, 1000)
    allocation = AllocationQualityMetric(Decimal("1.5"), Decimal("0.05"), Decimal("100.0"))

    # Stated confidence: 0.85 (mapped to parameter_deviation), is_invalidated = False (success)
    eval_1 = DecisionEvaluation(
        evaluation_id="eval-1",
        decision_id="dec-1",
        target=target,
        period=period,
        thesis_metrics=ThesisQualityMetric(Decimal("0.0225"), False, Decimal("0.85")),
        execution_metrics=execution,
        allocation_metrics=allocation,
        benchmarks=[],
        regime_id="BULL",
        created_at=datetime.now(timezone.utc)
    )
    # Stated confidence: 0.85, is_invalidated = True (failure)
    eval_2 = DecisionEvaluation(
        evaluation_id="eval-2",
        decision_id="dec-2",
        target=target,
        period=period,
        thesis_metrics=ThesisQualityMetric(Decimal("0.7225"), True, Decimal("0.85")),
        execution_metrics=execution,
        allocation_metrics=allocation,
        benchmarks=[],
        regime_id="BULL",
        created_at=datetime.now(timezone.utc)
    )
    
    record_repo.save(eval_1)
    record_repo.save(eval_2)

    # Get calibration table
    calib = calibration_service.build_calibration_table("WORKER", "worker-1", "BULL")
    
    # Bin for 0.80 - 0.90 is index 8 (0.8 to 0.9)
    target_bin = calib.bins[8]
    assert target_bin.prediction_count == 2
    assert target_bin.success_count == 1
    assert target_bin.calibrated_probability == Decimal("0.5")


# 9. Regime-conditioned calibration
def test_regime_conditioned_calibration():
    record_repo = InMemoryDecisionEvaluationRepository()
    calibration_service = CalibrationService(record_repo)
    
    target = EvaluationTarget("WORKER", "worker-1")
    period = EvaluationPeriod(datetime.now(timezone.utc), datetime.now(timezone.utc))
    execution = ExecutionQualityMetric(Decimal("5.0"), 100, 1000)
    allocation = AllocationQualityMetric(Decimal("1.5"), Decimal("0.05"), Decimal("100.0"))

    # In BULL: 1 success, 0 failures (100% success rate)
    eval_bull = DecisionEvaluation(
        evaluation_id="eval-bull",
        decision_id="dec-bull",
        target=target,
        period=period,
        thesis_metrics=ThesisQualityMetric(Decimal("0.04"), False, Decimal("0.85")),
        execution_metrics=execution,
        allocation_metrics=allocation,
        benchmarks=[],
        regime_id="BULL",
        created_at=datetime.now(timezone.utc)
    )
    # In BEAR: 0 success, 1 failure (0% success rate)
    eval_bear = DecisionEvaluation(
        evaluation_id="eval-bear",
        decision_id="dec-bear",
        target=target,
        period=period,
        thesis_metrics=ThesisQualityMetric(Decimal("0.04"), True, Decimal("0.85")),
        execution_metrics=execution,
        allocation_metrics=allocation,
        benchmarks=[],
        regime_id="BEAR",
        created_at=datetime.now(timezone.utc)
    )
    
    record_repo.save(eval_bull)
    record_repo.save(eval_bear)

    # Calibration in BULL should show 100% success for matched_evals
    # Note: get_calibrated_confidence checks matching target and regime
    calib_bull = calibration_service.get_calibrated_confidence("WORKER", "worker-1", Decimal("0.85"), "BULL")
    calib_bear = calibration_service.get_calibrated_confidence("WORKER", "worker-1", Decimal("0.85"), "BEAR")
    
    assert calib_bull == Decimal("1.0")
    assert calib_bear == Decimal("0.0")


# 10. File repository persistence
def test_file_repository_persistence(tmp_path):
    eval_dir = tmp_path / "evaluations"
    snap_dir = tmp_path / "snapshots"
    
    eval_repo = FileDecisionEvaluationRepository(storage_dir=str(eval_dir))
    snap_repo = FileEvaluationSnapshotRepository(storage_dir=str(snap_dir))

    target = EvaluationTarget("WORKER", "worker-1")
    period = EvaluationPeriod(datetime.now(timezone.utc), datetime.now(timezone.utc))
    thesis = ThesisQualityMetric(Decimal("0.04"), False, Decimal("0.1"))
    execution = ExecutionQualityMetric(Decimal("5.0"), 100, 1000)
    allocation = AllocationQualityMetric(Decimal("1.5"), Decimal("0.05"), Decimal("100.0"))
    benchmarks = [BenchmarkComparison("SPY", Decimal("50.0"), Decimal("0.05"), Decimal("4500.0"))]

    eval_obj = DecisionEvaluation(
        evaluation_id="eval-1",
        decision_id="dec-1",
        target=target,
        period=period,
        thesis_metrics=thesis,
        execution_metrics=execution,
        allocation_metrics=allocation,
        benchmarks=benchmarks,
        regime_id="BULL",
        created_at=datetime.now(timezone.utc),
        aggregate_version=1
    )

    eval_repo.save(eval_obj)
    
    # Assert file exists
    assert (eval_dir / "dec-1.json").exists()
    
    # Retrieve and check
    retrieved = eval_repo.find_by_decision("dec-1")
    assert retrieved is not None
    assert retrieved.evaluation_id == "eval-1"
    assert retrieved.thesis_metrics.brier_score == Decimal("0.04")
    
    # OCC conflict test in file repo
    eval_conflict = DecisionEvaluation(
        evaluation_id="eval-conflict",
        decision_id="dec-1",
        target=target,
        period=period,
        thesis_metrics=thesis,
        execution_metrics=execution,
        allocation_metrics=allocation,
        benchmarks=benchmarks,
        regime_id="BULL",
        created_at=datetime.now(timezone.utc),
        aggregate_version=1
    )
    with pytest.raises(ConcurrencyConflictError):
        eval_repo.save(eval_conflict)

    # Save snapshot
    snap_obj = EvaluationSnapshot(
        snapshot_id="snap-1",
        evaluation_id="eval-1",
        target=target,
        period=period,
        serialized_metrics="{}",
        created_at=datetime.now(timezone.utc)
    )
    snap_repo.save(snap_obj)
    assert (snap_dir / "snap-1.json").exists()

    # Clean up directories
    eval_repo.clear()
    snap_repo.clear()
    assert len(eval_repo.list_all()) == 0


# 11. In-memory repository persistence
def test_in_memory_repository_persistence():
    eval_repo = InMemoryDecisionEvaluationRepository()
    snap_repo = InMemoryEvaluationSnapshotRepository()

    target = EvaluationTarget("WORKER", "worker-1")
    period = EvaluationPeriod(datetime.now(timezone.utc), datetime.now(timezone.utc))
    thesis = ThesisQualityMetric(Decimal("0.04"), False, Decimal("0.1"))
    execution = ExecutionQualityMetric(Decimal("5.0"), 100, 1000)
    allocation = AllocationQualityMetric(Decimal("1.5"), Decimal("0.05"), Decimal("100.0"))

    eval_obj = DecisionEvaluation(
        evaluation_id="eval-1",
        decision_id="dec-1",
        target=target,
        period=period,
        thesis_metrics=thesis,
        execution_metrics=execution,
        allocation_metrics=allocation,
        benchmarks=[],
        regime_id="BULL",
        created_at=datetime.now(timezone.utc),
        aggregate_version=1
    )
    eval_repo.save(eval_obj)
    
    assert eval_repo.find_by_decision("dec-1") == eval_obj
    assert len(eval_repo.list_all()) == 1
    
    snap_obj = EvaluationSnapshot(
        snapshot_id="snap-1",
        evaluation_id="eval-1",
        target=target,
        period=period,
        serialized_metrics="{}",
        created_at=datetime.now(timezone.utc)
    )
    snap_repo.save(snap_obj)
    assert snap_repo.find_by_id("snap-1") == snap_obj
    assert snap_repo.list_by_target(target) == [snap_obj]
    
    eval_repo.clear()
    assert len(eval_repo.list_all()) == 0


# 12. Projection rebuild from history
def test_projection_rebuild_from_history():
    record_repo = InMemoryDecisionEvaluationRepository()
    events = []
    proj_service = ProjectionService(record_repo, events)
    
    target = EvaluationTarget("WORKER", "worker-1")
    period = EvaluationPeriod(datetime.now(timezone.utc), datetime.now(timezone.utc))
    execution = ExecutionQualityMetric(Decimal("5.0"), 100, 1000)
    allocation = AllocationQualityMetric(Decimal("1.5"), Decimal("0.05"), Decimal("100.0"))

    # Populate multiple records
    for i in range(5):
        eval_obj = DecisionEvaluation(
            evaluation_id=f"eval-{i}",
            decision_id=f"dec-{i}",
            target=target,
            period=period,
            thesis_metrics=ThesisQualityMetric(Decimal("0.01"), False, Decimal("0.1")),
            execution_metrics=execution,
            allocation_metrics=allocation,
            benchmarks=[],
            regime_id="BULL",
            created_at=datetime.now(timezone.utc),
            aggregate_version=1
        )
        record_repo.save(eval_obj)

    # Empty projections initially
    assert proj_service.get_worker_projection("worker-1") is None

    # Rebuild from history
    proj_service.rebuild_projections()
    
    # Assert projection was fully updated from all 5 records
    proj = proj_service.get_worker_projection("worker-1")
    assert proj is not None
    assert proj.total_decisions == 5
    assert proj.hit_rate == Decimal("1.0")


# 13. DecisionEvaluatedEvent replay safety
def test_decision_evaluated_event_replay_safety():
    record_repo = InMemoryDecisionEvaluationRepository()
    snapshot_repo = InMemoryEvaluationSnapshotRepository()
    events = []
    proj_service = ProjectionService(record_repo, events)
    eval_service = EvaluationService(record_repo, snapshot_repo, proj_service, events)

    # Ingest outcome once
    outcome = create_mock_outcome("dec-1")
    eval_service.consume_execution_outcome(outcome)
    
    assert len(record_repo.list_all()) == 1
    
    # Ingest same outcome again (replay event / idempotent check)
    # The evaluation service looks up existing evaluation for the decision.
    # If it exists, it increments the aggregate_version and saves, updating projections.
    # Let's ensure this works correctly and safely.
    eval_service.consume_execution_outcome(outcome)
    
    # We should have the same decision record updated to version 2
    all_evals = record_repo.list_all()
    assert len(all_evals) == 1
    assert all_evals[0].aggregate_version == 2
    
    # Event list should contain events for both runs
    assert len([e for e in events if isinstance(e, DecisionEvaluatedEvent)]) == 2
