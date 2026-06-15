from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict

@dataclass
class OutcomeRecorded:
    outcome_urn: str
    metric: str
    resolution_value: Decimal
    timestamp: datetime

@dataclass
class PerformanceEvaluated:
    eval_urn: str
    outcome_urn: str
    thesis_urn: str
    decision_urn: str
    worker_urn: str
    forecast_error: Decimal
    regime_distribution: Dict[str, Decimal]
    timestamp: datetime

@dataclass
class CalibrationAppended:
    ledger_urn: str
    worker_urn: str
    current_brier_score: Decimal
    timestamp: datetime
