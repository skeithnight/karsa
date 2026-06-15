from enum import Enum
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict
from karsa.performance.domain.exceptions import InvalidRegimeDistributionError, InvalidScoreError

class EvaluationHorizon(Enum):
    THIRTY_DAY = "30D"
    NINETY_DAY = "90D"
    ONE_EIGHTY_DAY = "180D"
    ONE_YEAR = "365D"

class OutcomeStatus(Enum):
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"

@dataclass(frozen=True)
class ForecastError:
    value: Decimal

@dataclass(frozen=True)
class BrierScore:
    value: Decimal

    def __post_init__(self):
        if self.value < Decimal('0.0') or self.value > Decimal('2.0'):
            raise InvalidScoreError("Brier score must be between 0.0 and 2.0")

@dataclass(frozen=True)
class RegimeDistribution:
    distribution: Dict[str, Decimal]

    def __post_init__(self):
        if not self.distribution:
            raise InvalidRegimeDistributionError("Regime distribution cannot be empty")
        
        total = sum(self.distribution.values())
        # Check against precision limits safely, rounding to 4 decimals for exactness
        if round(total, 4) != Decimal('1.0000'):
            raise InvalidRegimeDistributionError(f"Regime distribution must sum to 1.0, got {total}")
