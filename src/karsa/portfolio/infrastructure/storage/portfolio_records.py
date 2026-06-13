from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime

@dataclass
class PositionRecord:
    position_id: str
    symbol: str
    quantity: float
    average_cost: float
    market_value: float

@dataclass
class ExposureMetricsRecord:
    gross_exposure: float
    net_exposure: float
    concentration_exposure: float
    cash_ratio: float
    leverage_ratio: float

@dataclass
class PortfolioRecord:
    portfolio_id: str
    state: str
    current_target_snapshot_id: str
    positions: List[PositionRecord]
    exposure_metrics: ExposureMetricsRecord

@dataclass
class TargetPositionRecord:
    symbol: str
    target_weight: float

@dataclass
class PortfolioTargetSnapshotRecord:
    snapshot_id: str
    portfolio_id: str
    version: int
    target_positions: List[TargetPositionRecord]
    created_at: str

@dataclass
class PortfolioDecisionRecord:
    decision_id: str
    portfolio_id: str
    target_snapshot_id: str
    timestamp: str
    assumptions: Dict[str, str]
    constraints: Dict[str, str]
    expected_outcome: Dict[str, str]
    alternatives_considered: List[Dict[str, str]]
    decision_reasoning: str
