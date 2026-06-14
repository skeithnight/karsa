from dataclasses import dataclass
from datetime import datetime
from karsa.risk.exceptions import InvalidValueException

@dataclass(frozen=True)
class RiskSummaryProjection:
    evaluation_id: str
    portfolio_snapshot_id: str
    var_95: float
    var_99: float
    hhi: float
    gini: float
    created_at: datetime

    def __post_init__(self):
        if not self.evaluation_id or not self.evaluation_id.strip():
            raise InvalidValueException("evaluation_id cannot be empty")
        if not self.portfolio_snapshot_id or not self.portfolio_snapshot_id.strip():
            raise InvalidValueException("portfolio_snapshot_id cannot be empty")
        if self.var_95 < 0.0 or self.var_99 < 0.0:
            raise InvalidValueException("VaR values must be non-negative")
        if not (0.0 <= self.hhi <= 1.0) or not (0.0 <= self.gini <= 1.0):
            raise InvalidValueException("HHI and Gini must be between 0.0 and 1.0")
        if not isinstance(self.created_at, datetime):
            raise InvalidValueException("created_at must be a datetime instance")
