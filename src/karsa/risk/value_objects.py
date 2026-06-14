from dataclasses import dataclass
from typing import Dict, Any, List
from karsa.risk.exceptions import InvalidValueException

@dataclass(frozen=True)
class ValueAtRisk:
    confidence_level: float  # e.g., 0.95
    horizon_days: int
    value: float             # as a percentage of NAV or nominal amount

    def __post_init__(self):
        if not (0.0 < self.confidence_level < 1.0):
            raise InvalidValueException(f"Confidence level must be between 0.0 and 1.0 (got {self.confidence_level})")
        if self.horizon_days <= 0:
            raise InvalidValueException(f"Horizon days must be positive (got {self.horizon_days})")
        if self.value < 0.0:
            raise InvalidValueException(f"Value at Risk must be non-negative (got {self.value})")

@dataclass(frozen=True)
class ExpectedShortfall:
    confidence_level: float
    horizon_days: int
    value: float

    def __post_init__(self):
        if not (0.0 < self.confidence_level < 1.0):
            raise InvalidValueException(f"Confidence level must be between 0.0 and 1.0 (got {self.confidence_level})")
        if self.horizon_days <= 0:
            raise InvalidValueException(f"Horizon days must be positive (got {self.horizon_days})")
        if self.value < 0.0:
            raise InvalidValueException(f"Expected Shortfall must be non-negative (got {self.value})")

@dataclass(frozen=True)
class VolatilityForecast:
    asset_urn: str
    annualized_volatility: float

    def __post_init__(self):
        if not self.asset_urn or not self.asset_urn.strip():
            raise InvalidValueException("Asset URN cannot be empty")
        if self.annualized_volatility < 0.0:
            raise InvalidValueException(f"Volatility must be non-negative (got {self.annualized_volatility})")

@dataclass(frozen=True)
class CorrelationForecast:
    asset_urn_a: str
    asset_urn_b: str
    correlation: float

    def __post_init__(self):
        if not self.asset_urn_a or not self.asset_urn_a.strip():
            raise InvalidValueException("Asset URN A cannot be empty")
        if not self.asset_urn_b or not self.asset_urn_b.strip():
            raise InvalidValueException("Asset URN B cannot be empty")
        if not (-1.0 <= self.correlation <= 1.0):
            raise InvalidValueException(f"Correlation must be between -1.0 and 1.0 (got {self.correlation})")

@dataclass(frozen=True)
class ConcentrationRisk:
    hhi: float  # Herfindahl-Hirschman Index, 0.0 to 1.0
    gini: float # Gini Coefficient, 0.0 to 1.0
    top_5_weight: float

    def __post_init__(self):
        if not (0.0 <= self.hhi <= 1.0):
            raise InvalidValueException(f"HHI must be between 0.0 and 1.0 (got {self.hhi})")
        if not (0.0 <= self.gini <= 1.0):
            raise InvalidValueException(f"Gini coefficient must be between 0.0 and 1.0 (got {self.gini})")
        if not (0.0 <= self.top_5_weight <= 1.0):
            raise InvalidValueException(f"Top 5 weight must be between 0.0 and 1.0 (got {self.top_5_weight})")

@dataclass(frozen=True)
class LiquidityRisk:
    asset_urn: str
    days_to_liquidate: float
    liquidation_scenario_percent: float

    def __post_init__(self):
        if not self.asset_urn or not self.asset_urn.strip():
            raise InvalidValueException("Asset URN cannot be empty")
        if self.days_to_liquidate < 0.0:
            raise InvalidValueException(f"Days to liquidate must be non-negative (got {self.days_to_liquidate})")
        if not (0.0 < self.liquidation_scenario_percent <= 1.0):
            raise InvalidValueException(f"Liquidation scenario percent must be in (0.0, 1.0] (got {self.liquidation_scenario_percent})")

@dataclass(frozen=True)
class StressScenarioResult:
    scenario_urn: str
    portfolio_impact_percent: float
    shock_results: Dict[str, Any]

    def __post_init__(self):
        if not self.scenario_urn or not self.scenario_urn.strip():
            raise InvalidValueException("Scenario URN cannot be empty")
        if self.shock_results is None:
            raise InvalidValueException("Shock results dictionary cannot be None")

@dataclass(frozen=True)
class RegimeReference:
    regime_state_urn: str
    volatility_multiplier: float

    def __post_init__(self):
        if not self.regime_state_urn or not self.regime_state_urn.strip():
            raise InvalidValueException("Regime state URN cannot be empty")
        if not self.regime_state_urn.startswith("urn:karsa:regime:"):
            raise InvalidValueException(f"Regime state URN must start with 'urn:karsa:regime:' (got {self.regime_state_urn})")
        if self.volatility_multiplier <= 0.0:
            raise InvalidValueException(f"Volatility multiplier must be positive (got {self.volatility_multiplier})")

@dataclass(frozen=True)
class AssetExposure:
    asset_urn: str
    weight: float
    exposure_value: float
    sector: str

    def __post_init__(self):
        if not self.asset_urn or not self.asset_urn.strip():
            raise InvalidValueException("Asset URN cannot be empty")
        if not (-1.0 <= self.weight <= 1.0):
            raise InvalidValueException(f"Weight must be between -1.0 and 1.0 (got {self.weight})")
        if self.exposure_value < 0.0:
            raise InvalidValueException(f"Exposure value must be non-negative (got {self.exposure_value})")
