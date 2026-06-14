from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional
from enum import Enum

class PositionStatus(str, Enum):
    OPENING = "OPENING"
    OPEN = "OPEN"
    PARTIALLY_CLOSED = "PARTIALLY_CLOSED"
    CLOSED = "CLOSED"

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

@dataclass(frozen=True)
class HoldingLot:
    lot_id: str
    acquired_at: datetime
    units: Decimal
    price: Decimal

@dataclass(frozen=True)
class AssetExposure:
    asset_id: str
    exposure_pct: Decimal
    exposure_value: Decimal

@dataclass(frozen=True)
class BenchmarkReference:
    benchmark_id: str
    index_value: Decimal
    timestamp: datetime

@dataclass(frozen=True)
class PortfolioSnapshot:
    portfolio_id: str
    positions: List[Dict]
    cash_balance: Decimal
    net_asset_value: Decimal
    calculated_at: datetime
