from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

@dataclass(frozen=True)
class EvaluationTarget:
    target_type: str                    # e.g., "WORKER", "THESIS_VERSION", "BINDING"
    target_id: str                      # Unique context reference

@dataclass(frozen=True)
class EvaluationPeriod:
    start_time: datetime
    end_time: datetime

@dataclass(frozen=True)
class ThesisQualityMetric:
    brier_score: Decimal
    is_invalidated: bool
    parameter_deviation: Decimal

@dataclass(frozen=True)
class ExecutionQualityMetric:
    slippage_bps: Decimal
    fill_latency_ms: int
    token_count: int

@dataclass(frozen=True)
class AllocationQualityMetric:
    sharpe_ratio: Decimal
    drawdown_pct: Decimal
    excess_return_bps: Decimal

@dataclass(frozen=True)
class BenchmarkComparison:
    benchmark_name: str                 # e.g., "SPY", "QQQ"
    excess_return: Decimal
    drawdown_pct: Decimal
    index_snapshot_value: Decimal       # Frozen price at evaluation time

@dataclass(frozen=True)
class CalibrationBin:
    bin_range_start: Decimal            # e.g., 0.80
    bin_range_end: Decimal              # e.g., 0.90
    prediction_count: int
    success_count: int
    calibrated_probability: Decimal     # success_count / prediction_count

@dataclass(frozen=True)
class ConfidenceCalibration:
    bins: List[CalibrationBin]
