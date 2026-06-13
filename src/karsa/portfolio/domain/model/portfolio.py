from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, FrozenSet
from karsa.shared.domain.aggregate import VersionedAggregate

class PortfolioState(Enum):
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    REBALANCING = "REBALANCING"
    SUSPENDED = "SUSPENDED"
    LIQUIDATING = "LIQUIDATING"

class InvalidPortfolioStateTransitionError(Exception):
    pass

class ValidationException(Exception):
    pass

@dataclass
class Position:
    position_id: str
    portfolio_id: str
    symbol: str
    quantity: float
    average_cost: float
    market_value: float

@dataclass(frozen=True)
class TargetPosition:
    symbol: str
    target_weight: float

@dataclass(frozen=True)
class PortfolioTargetSnapshot:
    snapshot_id: str
    portfolio_id: str
    version: int
    target_positions: frozenset[TargetPosition]
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ExposureMetrics:
    gross_exposure: float
    net_exposure: float
    concentration_exposure: float
    cash_ratio: float
    leverage_ratio: float

    def __post_init__(self):
        if self.gross_exposure < 0 or self.net_exposure < 0 or self.concentration_exposure < 0 or self.cash_ratio < 0 or self.leverage_ratio < 0:
            raise ValidationException("ExposureMetrics values must not be negative")

@dataclass
class CashTarget:
    target_cash_percentage: float

    def __post_init__(self):
        if not (0.0 <= self.target_cash_percentage <= 1.0):
            raise ValidationException("CashTarget percentage must be between 0 and 1")

@dataclass
class PortfolioSnapshot:
    snapshot_id: str
    portfolio_id: str
    positions: List[Position]
    exposure_metrics: ExposureMetrics
    cash_target: CashTarget
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass(frozen=True)
class PortfolioDecision:
    decision_id: str
    portfolio_id: str
    target_snapshot_id: str
    timestamp: datetime
    assumptions: Dict[str, str]
    constraints: Dict[str, str]
    expected_outcome: Dict[str, str]
    alternatives_considered: List[Dict[str, str]]
    decision_reasoning: str

@dataclass
class AllocationPortfolioMapping:
    allocation_id: str
    portfolio_id: str
    allocation_weight: float
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if self.allocation_weight <= 0:
            raise ValidationException("allocation_weight must be > 0")

@dataclass
class TradeIntent:
    intent_id: str
    portfolio_id: str
    snapshot_id: str
    symbol: str
    action: str
    target_weight: float
    reason: str

@dataclass
class RegimeState:
    trend: str
    volatility: str
    liquidity: str
    confidence: float

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValidationException("RegimeState confidence must be between 0 and 1")

class Portfolio(VersionedAggregate):
    def __init__(self, portfolio_id: str):
        super().__init__()
        self.portfolio_id = portfolio_id
        self.state = PortfolioState.INITIALIZING
        self.positions: List[Position] = []
        self.exposure_metrics = ExposureMetrics(0, 0, 0, 1.0, 0)
        self.current_target_snapshot_id: Optional[str] = None

    def activate(self) -> None:
        if self.state not in [PortfolioState.INITIALIZING, PortfolioState.REBALANCING, PortfolioState.SUSPENDED]:
            raise InvalidPortfolioStateTransitionError(f"Cannot transition to ACTIVE from {self.state.name}")
        self.state = PortfolioState.ACTIVE

    def rebalance(self) -> None:
        if self.state not in [PortfolioState.ACTIVE]:
            raise InvalidPortfolioStateTransitionError(f"Cannot transition to REBALANCING from {self.state.name}")
        self.state = PortfolioState.REBALANCING

    def suspend(self) -> None:
        if self.state not in [PortfolioState.ACTIVE, PortfolioState.REBALANCING, PortfolioState.INITIALIZING]:
            raise InvalidPortfolioStateTransitionError(f"Cannot transition to SUSPENDED from {self.state.name}")
        self.state = PortfolioState.SUSPENDED

    def liquidate(self) -> None:
        if self.state not in [PortfolioState.ACTIVE, PortfolioState.REBALANCING, PortfolioState.SUSPENDED]:
            raise InvalidPortfolioStateTransitionError(f"Cannot transition to LIQUIDATING from {self.state.name}")
        self.state = PortfolioState.LIQUIDATING

    def update_exposure_metrics(self, metrics: ExposureMetrics) -> None:
        self.exposure_metrics = metrics

    def add_position(self, position: Position) -> None:
        self.positions.append(position)

@dataclass
class DriftMetrics:
    symbol: str
    target_weight: float
    actual_weight: float
    
    @property
    def drift_percentage(self) -> float:
        return abs(self.target_weight - self.actual_weight)

@dataclass
class RebalanceResult:
    portfolio_id: str
    decision: PortfolioDecision
    target_snapshot: PortfolioTargetSnapshot
    trade_intents: List[TradeIntent]
    drift_metrics: List[DriftMetrics]
    exposure_metrics: ExposureMetrics
