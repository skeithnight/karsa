import json
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional
from karsa.shared.domain.aggregate import VersionedAggregate
from karsa.portfolio.exceptions import DatabaseImmutabilityError
from karsa.portfolio.value_objects import PositionStatus, HoldingLot, AssetExposure

class PortfolioAggregate(VersionedAggregate):
    def __init__(self, portfolio_id: str, owner_id: str, base_currency: str = "USD", status: str = "ACTIVE", aggregate_version: int = 1):
        super().__init__(aggregate_version=aggregate_version)
        self.portfolio_id = portfolio_id
        self.owner_id = owner_id
        self.base_currency = base_currency
        self.status = status
        self._initialized = True

    def __setattr__(self, name, value):
        if getattr(self, "_initialized", False) and name in ["portfolio_id", "owner_id"]:
            raise TypeError("Cannot modify immutable properties of PortfolioAggregate")
        super().__setattr__(name, value)

class PositionAggregate(VersionedAggregate):
    def __init__(self, position_id: str, portfolio_id: str, asset_id: str, units: Decimal, average_cost: Decimal, status: PositionStatus = PositionStatus.OPEN, aggregate_version: int = 1):
        super().__init__(aggregate_version=aggregate_version)
        self.position_id = position_id
        self.portfolio_id = portfolio_id
        self.asset_id = asset_id
        self.units = units
        self.average_cost = average_cost
        self.status = status
        self.lots: List[HoldingLot] = []
        self._initialized = True

    def update_position(self, units_delta: Decimal, price: Decimal, lot_id: str, timestamp: datetime) -> None:
        new_units = self.units + units_delta
        if new_units < 0:
            raise ValueError("Position units cannot be negative")
        
        if units_delta > 0:
            # Add lot
            self.lots.append(HoldingLot(lot_id, timestamp, units_delta, price))
            total_cost = self.units * self.average_cost + units_delta * price
            self.average_cost = total_cost / new_units
        else:
            # Reduce units (FIFO or average cost basis, here we just adjust units and lots)
            pass
        
        self.units = new_units
        if self.units == 0:
            self.status = PositionStatus.CLOSED
        elif self.status == PositionStatus.OPENING:
            self.status = PositionStatus.OPEN
        else:
            self.status = PositionStatus.PARTIALLY_CLOSED if units_delta < 0 else PositionStatus.OPEN
            
        self.increment_version()

class CashLedgerAggregate(VersionedAggregate):
    def __init__(self, portfolio_id: str, available_balance: Decimal, held_balance: Decimal, currency: str = "USD", aggregate_version: int = 1):
        super().__init__(aggregate_version=aggregate_version)
        self.portfolio_id = portfolio_id
        self.available_balance = available_balance
        self.held_balance = held_balance
        self.currency = currency
        self._initialized = True

    def adjust_cash(self, delta: Decimal) -> None:
        if self.available_balance + delta < 0:
            from karsa.portfolio.exceptions import InsufficientFundsError
            raise InsufficientFundsError("Insufficient cash balance")
        self.available_balance += delta
        self.increment_version()

class ValuationAggregate(VersionedAggregate):
    def __init__(self, valuation_id: str, portfolio_id: str, net_asset_value: Decimal, cash_balance: Decimal, asset_valuations: Dict[str, Decimal], exposures: List[AssetExposure], benchmark_values: Dict[str, Decimal], calculated_at: datetime, aggregate_version: int = 1):
        super().__init__(aggregate_version=aggregate_version)
        self.valuation_id = valuation_id
        self.portfolio_id = portfolio_id
        self.net_asset_value = net_asset_value
        self.cash_balance = cash_balance
        self.asset_valuations = asset_valuations
        self.exposures = exposures
        self.benchmark_values = benchmark_values
        self.calculated_at = calculated_at
        self._initialized = True

    def __setattr__(self, name, value):
        if getattr(self, "_initialized", False):
            raise DatabaseImmutabilityError("Cannot modify immutable ValuationAggregate")
        super().__setattr__(name, value)
