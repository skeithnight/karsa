from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import List, Dict

@dataclass
class PositionProjection:
    portfolio_id: str
    asset_id: str
    units: Decimal
    average_cost: Decimal
    market_value: Decimal
    updated_at: datetime

@dataclass
class PortfolioValuationProjection:
    portfolio_id: str
    net_asset_value: Decimal
    cash_balance: Decimal
    total_positions_value: Decimal
    updated_at: datetime
