from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any

@dataclass
class HoldingsUpdatedEvent:
    event_id: str
    portfolio_id: str
    asset_id: str
    units_delta: str
    total_units: str
    average_cost: str
    timestamp: datetime
    correlation_id: str
    causation_id: str
    event_version: int = 1

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": "HoldingsUpdatedEvent",
            "portfolio_id": self.portfolio_id,
            "asset_id": self.asset_id,
            "units_delta": self.units_delta,
            "total_units": self.total_units,
            "average_cost": self.average_cost,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "event_version": self.event_version
        }

@dataclass
class CashUpdatedEvent:
    event_id: str
    portfolio_id: str
    available_balance: str
    held_balance: str
    currency: str
    timestamp: datetime
    correlation_id: str
    causation_id: str
    event_version: int = 1

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": "CashUpdatedEvent",
            "portfolio_id": self.portfolio_id,
            "available_balance": self.available_balance,
            "held_balance": self.held_balance,
            "currency": self.currency,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "event_version": self.event_version
        }

@dataclass
class PositionOpenedEvent:
    event_id: str
    portfolio_id: str
    position_id: str
    asset_id: str
    initial_units: str
    entry_price: str
    timestamp: datetime
    correlation_id: str
    causation_id: str
    event_version: int = 1

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": "PositionOpenedEvent",
            "portfolio_id": self.portfolio_id,
            "position_id": self.position_id,
            "asset_id": self.asset_id,
            "initial_units": self.initial_units,
            "entry_price": self.entry_price,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "event_version": self.event_version
        }

@dataclass
class PositionClosedEvent:
    event_id: str
    portfolio_id: str
    position_id: str
    asset_id: str
    realized_pnl: str
    timestamp: datetime
    correlation_id: str
    causation_id: str
    event_version: int = 1

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": "PositionClosedEvent",
            "portfolio_id": self.portfolio_id,
            "position_id": self.position_id,
            "asset_id": self.asset_id,
            "realized_pnl": self.realized_pnl,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "event_version": self.event_version
        }

@dataclass
class PortfolioValuationCalculatedEvent:
    event_id: str
    portfolio_id: str
    net_asset_value: str
    cash_balance: str
    asset_valuations: Dict[str, str]
    exposures: List[Dict[str, str]]
    benchmark_values: Dict[str, str]
    calculated_at: datetime
    correlation_id: str
    causation_id: str
    event_version: int = 1

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": "PortfolioValuationCalculatedEvent",
            "portfolio_id": self.portfolio_id,
            "net_asset_value": self.net_asset_value,
            "cash_balance": self.cash_balance,
            "asset_valuations": self.asset_valuations,
            "exposures": self.exposures,
            "benchmark_values": self.benchmark_values,
            "calculated_at": self.calculated_at.isoformat(),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "event_version": self.event_version
        }

@dataclass
class ExposureCalculatedEvent:
    event_id: str
    portfolio_id: str
    exposures: List[Dict[str, str]]
    timestamp: datetime
    correlation_id: str
    causation_id: str
    event_version: int = 1

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": "ExposureCalculatedEvent",
            "portfolio_id": self.portfolio_id,
            "exposures": self.exposures,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "event_version": self.event_version
        }
