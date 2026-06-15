from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass(frozen=True)
class RegimeDistribution:
    bull: Decimal
    bear: Decimal
    sideways: Decimal

@dataclass(frozen=True)
class PerformanceEvaluation:
    eval_urn: str
    outcome_urn: str
    journal_urn: str
    forecast_error: Decimal
    regime: RegimeDistribution
    created_at: datetime
