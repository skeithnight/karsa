from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class PerformanceEvaluation:
    target_type: str
    target_id: str
    hit_rate: Decimal
    brier_score: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    total_decisions: int
    updated_at: datetime


@dataclass
class ThesisPerformanceProjection:
    thesis_version_id: str
    brier_score: Decimal
    invalidation_triggered: bool
    total_predictions: int
    updated_at: datetime


@dataclass
class WorkerPerformanceProjection:
    worker_id: str
    hit_rate: Decimal
    brier_score: Decimal
    calibrated_confidence: Decimal
    total_decisions: int
    updated_at: datetime


@dataclass
class StrategyPerformanceProjection:
    strategy_id: str
    excess_return_bps: Decimal
    max_drawdown: Decimal
    sharpe_ratio: Decimal
    updated_at: datetime


@dataclass
class ThesisExecutionBindingPerformanceProjection:
    binding_id: str
    thesis_version_id: str
    portfolio_id: str
    strategy_id: str
    excess_return_bps: Decimal
    max_drawdown: Decimal
    allocation_limit: Decimal
    status: str
    updated_at: datetime
