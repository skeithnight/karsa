from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional
import re

from karsa.risk.exceptions import (
    ImmutabilityViolationException,
    NegativeEigenvalueException,
    InvalidSnapshotURNException,
    InvalidValueException,
)
from karsa.risk.value_objects import (
    ValueAtRisk,
    ExpectedShortfall,
    VolatilityForecast,
    CorrelationForecast,
    ConcentrationRisk,
    LiquidityRisk,
    StressScenarioResult,
    RegimeReference,
    AssetExposure,
)

class ImmutableAggregate:
    """Base class for strictly immutable aggregates that prevent property modification at runtime."""
    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise ImmutabilityViolationException("Cannot modify property of an immutable aggregate.")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        raise ImmutabilityViolationException("Cannot delete property of an immutable aggregate.")

@dataclass
class RiskEvaluationRecord(ImmutableAggregate):
    evaluation_id: str
    portfolio_snapshot_id: str
    model_id: str
    model_version: str
    methodology_version: str
    covariance_version: str
    stress_scenario_version: str
    regime_state_urn: str
    risk_metrics: List[ValueAtRisk]
    expected_shortfalls: List[ExpectedShortfall]
    exposures: List[AssetExposure]
    concentration_risk: ConcentrationRisk
    liquidity_risks: List[LiquidityRisk]
    created_at: datetime

    def __post_init__(self):
        if not self.evaluation_id or not self.evaluation_id.strip():
            raise InvalidValueException("evaluation_id cannot be empty")
        if not self.portfolio_snapshot_id or not self.portfolio_snapshot_id.strip():
            raise InvalidSnapshotURNException("portfolio_snapshot_id cannot be empty")
        if not self.portfolio_snapshot_id.startswith("urn:karsa:portfolio:snapshot:"):
            raise InvalidSnapshotURNException(
                f"portfolio_snapshot_id must start with 'urn:karsa:portfolio:snapshot:' (got {self.portfolio_snapshot_id})"
            )
        if not self.model_id or not self.model_id.strip():
            raise InvalidValueException("model_id cannot be empty")
        if not self.model_version or not self.model_version.strip():
            raise InvalidValueException("model_version cannot be empty")
        if not self.methodology_version or not self.methodology_version.strip():
            raise InvalidValueException("methodology_version cannot be empty")
        if not self.covariance_version or not self.covariance_version.strip():
            raise InvalidValueException("covariance_version cannot be empty")
        if not self.stress_scenario_version or not self.stress_scenario_version.strip():
            raise InvalidValueException("stress_scenario_version cannot be empty")
        if not self.regime_state_urn or not self.regime_state_urn.strip():
            raise InvalidValueException("regime_state_urn cannot be empty")
        if not self.regime_state_urn.startswith("urn:karsa:regime:"):
            raise InvalidValueException(
                f"regime_state_urn must start with 'urn:karsa:regime:' (got {self.regime_state_urn})"
            )
        if not isinstance(self.risk_metrics, list) or not all(isinstance(x, ValueAtRisk) for x in self.risk_metrics):
            raise InvalidValueException("risk_metrics must be a list of ValueAtRisk instances")
        if not isinstance(self.expected_shortfalls, list) or not all(isinstance(x, ExpectedShortfall) for x in self.expected_shortfalls):
            raise InvalidValueException("expected_shortfalls must be a list of ExpectedShortfall instances")
        if not isinstance(self.exposures, list) or not all(isinstance(x, AssetExposure) for x in self.exposures):
            raise InvalidValueException("exposures must be a list of AssetExposure instances")
        if not isinstance(self.concentration_risk, ConcentrationRisk):
            raise InvalidValueException("concentration_risk must be a ConcentrationRisk instance")
        if not isinstance(self.liquidity_risks, list) or not all(isinstance(x, LiquidityRisk) for x in self.liquidity_risks):
            raise InvalidValueException("liquidity_risks must be a list of LiquidityRisk instances")
        if not isinstance(self.created_at, datetime):
            raise InvalidValueException("created_at must be a datetime instance")

@dataclass
class CovarianceForecast(ImmutableAggregate):
    forecast_id: str
    matrix_urn: str
    universe_size: int
    created_at: datetime

    def __post_init__(self):
        if not self.forecast_id or not self.forecast_id.strip():
            raise InvalidValueException("forecast_id cannot be empty")
        if not self.matrix_urn or not self.matrix_urn.strip():
            raise InvalidValueException("matrix_urn cannot be empty")
        if not self.matrix_urn.startswith("urn:karsa:risk:covariance:"):
            raise InvalidValueException(
                f"matrix_urn must start with 'urn:karsa:risk:covariance:' (got {self.matrix_urn})"
            )
        if self.universe_size <= 0:
            raise InvalidValueException(f"universe_size must be positive (got {self.universe_size})")
        if not isinstance(self.created_at, datetime):
            raise InvalidValueException("created_at must be a datetime instance")

@dataclass
class StressEvaluationRecord(ImmutableAggregate):
    stress_evaluation_id: str
    portfolio_snapshot_id: str
    scenario_urn: str
    shock_results: StressScenarioResult
    created_at: datetime

    def __post_init__(self):
        if not self.stress_evaluation_id or not self.stress_evaluation_id.strip():
            raise InvalidValueException("stress_evaluation_id cannot be empty")
        if not self.portfolio_snapshot_id or not self.portfolio_snapshot_id.strip():
            raise InvalidSnapshotURNException("portfolio_snapshot_id cannot be empty")
        if not self.portfolio_snapshot_id.startswith("urn:karsa:portfolio:snapshot:"):
            raise InvalidSnapshotURNException(
                f"portfolio_snapshot_id must start with 'urn:karsa:portfolio:snapshot:' (got {self.portfolio_snapshot_id})"
            )
        if not self.scenario_urn or not self.scenario_urn.strip():
            raise InvalidValueException("scenario_urn cannot be empty")
        if not self.scenario_urn.startswith("urn:karsa:risk:scenario:"):
            raise InvalidValueException(
                f"scenario_urn must start with 'urn:karsa:risk:scenario:' (got {self.scenario_urn})"
            )
        if not isinstance(self.shock_results, StressScenarioResult):
            raise InvalidValueException("shock_results must be a StressScenarioResult instance")
        if not isinstance(self.created_at, datetime):
            raise InvalidValueException("created_at must be a datetime instance")
