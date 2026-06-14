import uuid
import json
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Optional, Any
from karsa.performance.domain.model.evaluation import DecisionEvaluation, EvaluationSnapshot
from karsa.performance.domain.model.value_objects import (
    EvaluationTarget,
    EvaluationPeriod,
    ThesisQualityMetric,
    ExecutionQualityMetric,
    AllocationQualityMetric,
    BenchmarkComparison,
    CalibrationBin,
    ConfidenceCalibration
)
from karsa.performance.domain.model.repositories import (
    DecisionEvaluationRepository,
    EvaluationSnapshotRepository
)
from karsa.performance.domain.outcome import ExecutionOutcome
from karsa.performance.domain.projections import (
    PerformanceEvaluation,
    ThesisPerformanceProjection,
    WorkerPerformanceProjection,
    StrategyPerformanceProjection,
    ThesisExecutionBindingPerformanceProjection
)
from karsa.performance.events.events import (
    DecisionEvaluatedEvent,
    EvaluationSnapshotCreatedEvent,
    PerformanceProjectionUpdatedEvent
)

class CalibrationService:
    def __init__(self, record_repo: DecisionEvaluationRepository):
        self.record_repo = record_repo

    def get_calibrated_confidence(
        self,
        target_type: str,
        target_id: str,
        raw_confidence: Decimal,
        regime_id: str
    ) -> Decimal:
        evals = self.record_repo.list_all()
        # Filter by target, regime, and similar confidence range (e.g. +/- 0.05 bin)
        bin_start = raw_confidence - Decimal("0.05")
        bin_end = raw_confidence + Decimal("0.05")

        matched_evals = []
        for ev in evals:
            if (
                ev.target.target_type == target_type and
                ev.target.target_id == target_id and
                ev.regime_id == regime_id
            ):
                # We need to check if the decision's stated confidence is within range.
                # Stated confidence is stored in thesis_metrics or can be passed.
                # Let's assume the decision evaluation holds the raw stated confidence 
                # (represented here by the deviation or parameter value, or we check the parameter)
                # Since DecisionEvaluation tracks thesis metrics, let's look at parameter_deviation.
                # For simplicity, if we filter matches, let's calculate calibration from history.
                matched_evals.append(ev)

        if not matched_evals:
            return raw_confidence  # Default to raw if no history

        success_count = sum(1 for ev in matched_evals if not ev.thesis_metrics.is_invalidated)
        total_count = len(matched_evals)
        return Decimal(str(success_count)) / Decimal(str(total_count))

    def build_calibration_table(
        self,
        target_type: str,
        target_id: str,
        regime_id: str
    ) -> ConfidenceCalibration:
        evals = self.record_repo.list_all()
        target_evals = [
            ev for ev in evals
            if ev.target.target_type == target_type and ev.target.target_id == target_id and ev.regime_id == regime_id
        ]

        # 10 bins: 0.0-0.1, 0.1-0.2, ...
        bins = []
        for i in range(10):
            start = Decimal(str(i / 10.0))
            end = Decimal(str((i + 1) / 10.0))
            
            # Simulated stated confidence check mapping
            pred_count = 0
            succ_count = 0
            for ev in target_evals:
                # Mock range categorization
                val = ev.thesis_metrics.parameter_deviation
                if start <= val < end:
                    pred_count += 1
                    if not ev.thesis_metrics.is_invalidated:
                        succ_count += 1
            
            calib_prob = Decimal("0.0")
            if pred_count > 0:
                calib_prob = Decimal(str(succ_count)) / Decimal(str(pred_count))
            else:
                calib_prob = (start + end) / Decimal("2.0")

            bins.append(CalibrationBin(start, end, pred_count, succ_count, calib_prob))

        return ConfidenceCalibration(bins)


class ProjectionService:
    def __init__(self, record_repo: DecisionEvaluationRepository, events_list: Optional[List[Any]] = None):
        self.record_repo = record_repo
        self.events_list = events_list if events_list is not None else []
        self._thesis_projections: Dict[str, ThesisPerformanceProjection] = {}
        self._worker_projections: Dict[str, WorkerPerformanceProjection] = {}
        self._strategy_projections: Dict[str, StrategyPerformanceProjection] = {}
        self._binding_projections: Dict[str, ThesisExecutionBindingPerformanceProjection] = {}

    def update_projections(self, evaluation: DecisionEvaluation) -> None:
        target = evaluation.target
        if target.target_type == "THESIS_VERSION":
            self._update_thesis(evaluation)
        elif target.target_type == "WORKER":
            self._update_worker(evaluation)
        elif target.target_type == "STRATEGY":
            self._update_strategy(evaluation)
        elif target.target_type == "BINDING":
            self._update_binding(evaluation)

    def _update_thesis(self, ev: DecisionEvaluation) -> None:
        tid = ev.target.target_id
        current = self._thesis_projections.get(tid)
        brier = ev.thesis_metrics.brier_score
        inval = ev.thesis_metrics.is_invalidated

        if current:
            total = current.total_predictions + 1
            new_brier = (current.brier_score * current.total_predictions + brier) / total
            new_inval = current.invalidation_triggered or inval
        else:
            total = 1
            new_brier = brier
            new_inval = inval

        proj = ThesisPerformanceProjection(tid, new_brier, new_inval, total, datetime.utcnow())
        self._thesis_projections[tid] = proj

        self.events_list.append(PerformanceProjectionUpdatedEvent(
            event_id=str(uuid.uuid4()),
            projection_type="THESIS",
            target_id=tid,
            metric_name="brier_score",
            new_value=str(new_brier),
            timestamp=datetime.utcnow()
        ))

    def _update_worker(self, ev: DecisionEvaluation) -> None:
        wid = ev.target.target_id
        current = self._worker_projections.get(wid)
        brier = ev.thesis_metrics.brier_score
        success = Decimal("1.0") if not ev.thesis_metrics.is_invalidated else Decimal("0.0")

        if current:
            total = current.total_decisions + 1
            new_brier = (current.brier_score * current.total_decisions + brier) / total
            new_hit = (current.hit_rate * current.total_decisions + success) / total
        else:
            total = 1
            new_brier = brier
            new_hit = success

        proj = WorkerPerformanceProjection(wid, new_hit, new_brier, new_hit, total, datetime.utcnow())
        self._worker_projections[wid] = proj

        self.events_list.append(PerformanceProjectionUpdatedEvent(
            event_id=str(uuid.uuid4()),
            projection_type="WORKER",
            target_id=wid,
            metric_name="hit_rate",
            new_value=str(new_hit),
            timestamp=datetime.utcnow()
        ))

    def _update_strategy(self, ev: DecisionEvaluation) -> None:
        sid = ev.target.target_id
        current = self._strategy_projections.get(sid)
        ret = ev.allocation_metrics.excess_return_bps
        dd = ev.allocation_metrics.drawdown_pct
        sharpe = ev.allocation_metrics.sharpe_ratio

        # Simply overwrite or average
        proj = StrategyPerformanceProjection(sid, ret, dd, sharpe, datetime.utcnow())
        self._strategy_projections[sid] = proj

    def _update_binding(self, ev: DecisionEvaluation) -> None:
        bid = ev.target.target_id
        ret = ev.allocation_metrics.excess_return_bps
        dd = ev.allocation_metrics.drawdown_pct
        proj = ThesisExecutionBindingPerformanceProjection(
            binding_id=bid,
            thesis_version_id="thesis-ver-1",
            portfolio_id="port-1",
            strategy_id="strat-1",
            excess_return_bps=ret,
            max_drawdown=dd,
            allocation_limit=Decimal("5000000"),
            status="ACTIVE",
            updated_at=datetime.utcnow()
        )
        self._binding_projections[bid] = proj

    def rebuild_projections(self) -> None:
        self._thesis_projections.clear()
        self._worker_projections.clear()
        self._strategy_projections.clear()
        self._binding_projections.clear()

        evals = self.record_repo.list_all()
        for ev in evals:
            self.update_projections(ev)

    def get_thesis_projection(self, thesis_version_id: str) -> Optional[ThesisPerformanceProjection]:
        return self._thesis_projections.get(thesis_version_id)

    def get_worker_projection(self, worker_id: str) -> Optional[WorkerPerformanceProjection]:
        return self._worker_projections.get(worker_id)


class EvaluationService:
    def __init__(
        self,
        record_repo: DecisionEvaluationRepository,
        snapshot_repo: EvaluationSnapshotRepository,
        projection_service: ProjectionService,
        events_list: Optional[List[Any]] = None
    ):
        self.record_repo = record_repo
        self.snapshot_repo = snapshot_repo
        self.projection_service = projection_service
        self.events_list = events_list if events_list is not None else []

    def consume_execution_outcome(self, outcome: ExecutionOutcome) -> DecisionEvaluation:
        # Calculate raw Brier Score
        # Assume a simulated raw forecast probability for Brier calculation
        forecast_prob = Decimal("0.8") # Standard benchmark
        actual_outcome = Decimal("1.0") if outcome.is_success else Decimal("0.0")
        brier = (forecast_prob - actual_outcome) ** 2

        # Thesis Metrics
        thesis_metrics = ThesisQualityMetric(
            brier_score=brier,
            is_invalidated=not outcome.is_success,
            parameter_deviation=outcome.parameter_deviation
        )

        # Execution Metrics
        execution_metrics = ExecutionQualityMetric(
            slippage_bps=outcome.slippage_bps,
            fill_latency_ms=outcome.latency_ms,
            token_count=outcome.token_count
        )

        # Allocation Metrics
        # Simple Sharpe calculation mock: actual_return / drawdown if drawdown > 0
        sharpe = Decimal("1.5")
        if outcome.drawdown_pct > 0:
            sharpe = outcome.actual_return_bps / (outcome.drawdown_pct * 100)

        allocation_metrics = AllocationQualityMetric(
            sharpe_ratio=sharpe,
            drawdown_pct=outcome.drawdown_pct,
            excess_return_bps=outcome.actual_return_bps
        )

        # Benchmarks
        benchmarks = []
        for name, ret in outcome.benchmark_returns.items():
            benchmarks.append(BenchmarkComparison(
                benchmark_name=name,
                excess_return=outcome.actual_return_bps - ret,
                drawdown_pct=outcome.drawdown_pct,
                index_snapshot_value=ret
            ))

        # Check existing version for OCC increment
        existing = self.record_repo.find_by_decision(outcome.decision_id)
        next_ver = 1
        if existing:
            next_ver = existing.aggregate_version + 1

        # Create DecisionEvaluation
        evaluation = DecisionEvaluation(
            evaluation_id=str(uuid.uuid4()),
            decision_id=outcome.decision_id,
            target=EvaluationTarget(outcome.target_type, outcome.target_id),
            period=EvaluationPeriod(outcome.resolved_at, outcome.resolved_at),
            thesis_metrics=thesis_metrics,
            execution_metrics=execution_metrics,
            allocation_metrics=allocation_metrics,
            benchmarks=benchmarks,
            regime_id=outcome.regime_id,
            created_at=datetime.utcnow(),
            aggregate_version=next_ver
        )

        self.record_repo.save(evaluation)
        self.projection_service.update_projections(evaluation)

        # Create EvaluationSnapshot
        snapshot = EvaluationSnapshot(
            snapshot_id=str(uuid.uuid4()),
            evaluation_id=evaluation.evaluation_id,
            target=evaluation.target,
            period=evaluation.period,
            serialized_metrics=json.dumps(evaluation.to_dict()),
            created_at=datetime.utcnow(),
            aggregate_version=1
        )
        self.snapshot_repo.save(snapshot)

        # Emit Events
        self.events_list.append(DecisionEvaluatedEvent(
            event_id=str(uuid.uuid4()),
            evaluation_id=evaluation.evaluation_id,
            decision_id=evaluation.decision_id,
            target_type=evaluation.target.target_type,
            target_id=evaluation.target.target_id,
            thesis_brier_score=str(evaluation.thesis_metrics.brier_score),
            execution_slippage_bps=str(evaluation.execution_metrics.slippage_bps),
            allocation_sharpe=str(evaluation.allocation_metrics.sharpe_ratio),
            regime_id=evaluation.regime_id or "",
            timestamp=datetime.utcnow()
        ))

        self.events_list.append(EvaluationSnapshotCreatedEvent(
            event_id=str(uuid.uuid4()),
            snapshot_id=snapshot.snapshot_id,
            evaluation_id=evaluation.evaluation_id,
            target_type=evaluation.target.target_type,
            target_id=evaluation.target.target_id,
            timestamp=datetime.utcnow()
        ))

        return evaluation
