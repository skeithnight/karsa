from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List

@dataclass(frozen=True)
class RiskEvaluationCreatedEvent:
    event_id: str
    correlation_id: str
    causation_id: str
    timestamp: datetime
    evaluation_id: str
    portfolio_snapshot_id: str
    risk_metrics: Dict[str, Any]
    concentration: Dict[str, Any]
    event_version: int = 1

@dataclass(frozen=True)
class CovarianceForecastUpdatedEvent:
    event_id: str
    correlation_id: str
    causation_id: str
    timestamp: datetime
    forecast_id: str
    matrix_urn: str
    universe_size: int
    event_version: int = 1

@dataclass(frozen=True)
class StressEvaluationCreatedEvent:
    event_id: str
    correlation_id: str
    causation_id: str
    timestamp: datetime
    stress_evaluation_id: str
    portfolio_snapshot_id: str
    scenario_urn: str
    shock_results: Dict[str, Any]
    event_version: int = 1
