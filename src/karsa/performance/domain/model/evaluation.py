import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from karsa.shared.domain.aggregate import VersionedAggregate
from karsa.performance.domain.model.value_objects import (
    EvaluationTarget,
    EvaluationPeriod,
    ThesisQualityMetric,
    ExecutionQualityMetric,
    AllocationQualityMetric,
    BenchmarkComparison
)

class DecisionEvaluation(VersionedAggregate):
    def __init__(
        self,
        evaluation_id: str,
        decision_id: str,
        target: EvaluationTarget,
        period: EvaluationPeriod,
        thesis_metrics: ThesisQualityMetric,
        execution_metrics: ExecutionQualityMetric,
        allocation_metrics: AllocationQualityMetric,
        benchmarks: List[BenchmarkComparison],
        regime_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.evaluation_id = evaluation_id
        self.decision_id = decision_id
        self.target = target
        self.period = period
        self.thesis_metrics = thesis_metrics
        self.execution_metrics = execution_metrics
        self.allocation_metrics = allocation_metrics
        self.benchmarks = benchmarks
        self.regime_id = regime_id
        self.created_at = created_at or datetime.utcnow()
        self._initialized = True

    def __setattr__(self, name, value):
        if getattr(self, "_initialized", False):
            raise TypeError("Cannot modify immutable DecisionEvaluation aggregate")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if getattr(self, "_initialized", False):
            raise TypeError("Cannot modify immutable DecisionEvaluation aggregate")
        super().__delattr__(name)

    def to_dict(self) -> dict:
        return {
            "evaluation_id": self.evaluation_id,
            "decision_id": self.decision_id,
            "target": {
                "target_type": self.target.target_type,
                "target_id": self.target.target_id
            },
            "period": {
                "start_time": self.period.start_time.isoformat(),
                "end_time": self.period.end_time.isoformat()
            },
            "thesis_metrics": {
                "brier_score": str(self.thesis_metrics.brier_score),
                "is_invalidated": self.thesis_metrics.is_invalidated,
                "parameter_deviation": str(self.thesis_metrics.parameter_deviation)
            },
            "execution_metrics": {
                "slippage_bps": str(self.execution_metrics.slippage_bps),
                "fill_latency_ms": self.execution_metrics.fill_latency_ms,
                "token_count": self.execution_metrics.token_count
            },
            "allocation_metrics": {
                "sharpe_ratio": str(self.allocation_metrics.sharpe_ratio),
                "drawdown_pct": str(self.allocation_metrics.drawdown_pct),
                "excess_return_bps": str(self.allocation_metrics.excess_return_bps)
            },
            "benchmarks": [
                {
                    "benchmark_name": b.benchmark_name,
                    "excess_return": str(b.excess_return),
                    "drawdown_pct": str(b.drawdown_pct),
                    "index_snapshot_value": str(b.index_snapshot_value)
                } for b in self.benchmarks
            ],
            "regime_id": self.regime_id,
            "created_at": self.created_at.isoformat(),
            "aggregate_version": self.aggregate_version
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DecisionEvaluation':
        from decimal import Decimal
        target = EvaluationTarget(
            target_type=data["target"]["target_type"],
            target_id=data["target"]["target_id"]
        )
        period = EvaluationPeriod(
            start_time=datetime.fromisoformat(data["period"]["start_time"]),
            end_time=datetime.fromisoformat(data["period"]["end_time"])
        )
        thesis = ThesisQualityMetric(
            brier_score=Decimal(data["thesis_metrics"]["brier_score"]),
            is_invalidated=data["thesis_metrics"]["is_invalidated"],
            parameter_deviation=Decimal(data["thesis_metrics"]["parameter_deviation"])
        )
        execution = ExecutionQualityMetric(
            slippage_bps=Decimal(data["execution_metrics"]["slippage_bps"]),
            fill_latency_ms=data["execution_metrics"]["fill_latency_ms"],
            token_count=data["execution_metrics"]["token_count"]
        )
        allocation = AllocationQualityMetric(
            sharpe_ratio=Decimal(data["allocation_metrics"]["sharpe_ratio"]),
            drawdown_pct=Decimal(data["allocation_metrics"]["drawdown_pct"]),
            excess_return_bps=Decimal(data["allocation_metrics"]["excess_return_bps"])
        )
        benchmarks = [
            BenchmarkComparison(
                benchmark_name=b["benchmark_name"],
                excess_return=Decimal(b["excess_return"]),
                drawdown_pct=Decimal(b["drawdown_pct"]),
                index_snapshot_value=Decimal(b["index_snapshot_value"])
            ) for b in data["benchmarks"]
        ]
        created_at = datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"]
        return cls(
            evaluation_id=data["evaluation_id"],
            decision_id=data["decision_id"],
            target=target,
            period=period,
            thesis_metrics=thesis,
            execution_metrics=execution,
            allocation_metrics=allocation,
            benchmarks=benchmarks,
            regime_id=data.get("regime_id"),
            created_at=created_at,
            aggregate_version=data.get("aggregate_version", 1)
        )


class EvaluationSnapshot(VersionedAggregate):
    def __init__(
        self,
        snapshot_id: str,
        evaluation_id: str,
        target: EvaluationTarget,
        period: EvaluationPeriod,
        serialized_metrics: str,
        created_at: Optional[datetime] = None,
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.snapshot_id = snapshot_id
        self.evaluation_id = evaluation_id
        self.target = target
        self.period = period
        self.serialized_metrics = serialized_metrics
        self.created_at = created_at or datetime.utcnow()
        self._initialized = True

    def __setattr__(self, name, value):
        if getattr(self, "_initialized", False):
            raise TypeError("Cannot modify immutable EvaluationSnapshot aggregate")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if getattr(self, "_initialized", False):
            raise TypeError("Cannot modify immutable EvaluationSnapshot aggregate")
        super().__delattr__(name)

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "evaluation_id": self.evaluation_id,
            "target": {
                "target_type": self.target.target_type,
                "target_id": self.target.target_id
            },
            "period": {
                "start_time": self.period.start_time.isoformat(),
                "end_time": self.period.end_time.isoformat()
            },
            "serialized_metrics": self.serialized_metrics,
            "created_at": self.created_at.isoformat(),
            "aggregate_version": self.aggregate_version
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'EvaluationSnapshot':
        target = EvaluationTarget(
            target_type=data["target"]["target_type"],
            target_id=data["target"]["target_id"]
        )
        period = EvaluationPeriod(
            start_time=datetime.fromisoformat(data["period"]["start_time"]),
            end_time=datetime.fromisoformat(data["period"]["end_time"])
        )
        created_at = datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"]
        return cls(
            snapshot_id=data["snapshot_id"],
            evaluation_id=data["evaluation_id"],
            target=target,
            period=period,
            serialized_metrics=data["serialized_metrics"],
            created_at=created_at,
            aggregate_version=data.get("aggregate_version", 1)
        )
