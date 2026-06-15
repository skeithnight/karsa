from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from decimal import Decimal
from karsa.performance.domain.value_objects import OutcomeStatus, ForecastError, BrierScore, RegimeDistribution, EvaluationHorizon

class OutcomeRecord:
    def __init__(self, outcome_urn: str, metric: str, target_value: Decimal, resolution_date: datetime,
                 final_value: Optional[Decimal] = None, status: OutcomeStatus = OutcomeStatus.PENDING):
        self.outcome_urn = outcome_urn
        self.metric = metric
        self.target_value = target_value
        self.resolution_date = resolution_date
        self.final_value = final_value
        self.status = status

    def resolve(self, final_value: Decimal):
        self.final_value = final_value
        self.status = OutcomeStatus.RESOLVED

    def fail(self):
        self.status = OutcomeStatus.FAILED

class PerformanceEvaluation:
    def __init__(self, eval_urn: str, outcome_urn: str, thesis_urn: str, decision_urn: str,
                 worker_urn: str, forecast_error: ForecastError, regime_distribution: RegimeDistribution,
                 horizon: EvaluationHorizon, created_at: datetime):
        self.eval_urn = eval_urn
        self.outcome_urn = outcome_urn
        self.thesis_urn = thesis_urn
        self.decision_urn = decision_urn
        self.worker_urn = worker_urn
        self.forecast_error = forecast_error
        self.regime_distribution = regime_distribution
        self.horizon = horizon
        self.created_at = created_at

class CalibrationLedgerEntry:
    def __init__(self, ledger_urn: str, previous_ledger_urn: Optional[str], worker_urn: str,
                 brier_score: BrierScore, created_at: datetime):
        self.ledger_urn = ledger_urn
        self.previous_ledger_urn = previous_ledger_urn
        self.worker_urn = worker_urn
        self.brier_score = brier_score
        self.created_at = created_at
