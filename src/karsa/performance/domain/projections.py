from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, date
from typing import Optional
from .value_objects import DecisionPerformanceIdentity

@dataclass
class DecisionContext:
    decision_id: str
    worker_id: str
    strategy_id: str
    thesis_id: str
    stated_confidence: Optional[Decimal]
    decision_timestamp: datetime

@dataclass
class DecisionPerformanceRecord:
    identity: DecisionPerformanceIdentity
    worker_id: str
    strategy_id: str
    thesis_id: str
    regime_id: Optional[str]
    gross_pnl: Decimal
    net_pnl: Decimal
    stated_confidence: Optional[Decimal]
    decision_timestamp: datetime
    projection_schema_version: int = 1
    calculation_version: int = 1

@dataclass
class DailyPnlBucket:
    target_type: str
    target_id: str
    bucket_date: date
    daily_gross_pnl: Decimal
    daily_net_pnl: Decimal

@dataclass
class WorkerPerformanceProfile:
    worker_id: str
    cumulative_gross_pnl: Decimal
    max_drawdown: Decimal
    sharpe_proxy: Decimal
    hit_rate: Decimal
    brier_score: Optional[Decimal]
    last_updated_at: datetime
    calculation_version: int = 1

# Other profiles follow the exact same structure dynamically driven by target_type
