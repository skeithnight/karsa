import os
import json
import copy
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime
from karsa.portfolio.models import PortfolioAggregate, PositionAggregate, CashLedgerAggregate, ValuationAggregate
from karsa.portfolio.exceptions import ConcurrencyConflictError, DatabaseImmutabilityError

class PortfolioRepository(ABC):
    @abstractmethod
    def save(self, portfolio: PortfolioAggregate) -> None:
        pass
    @abstractmethod
    def find_by_id(self, portfolio_id: str) -> Optional[PortfolioAggregate]:
        pass

class PositionRepository(ABC):
    @abstractmethod
    def save(self, position: PositionAggregate) -> None:
        pass
    @abstractmethod
    def find_by_portfolio_and_asset(self, portfolio_id: str, asset_id: str) -> Optional[PositionAggregate]:
        pass
    @abstractmethod
    def list_active_by_portfolio(self, portfolio_id: str) -> List[PositionAggregate]:
        pass

class CashLedgerRepository(ABC):
    @abstractmethod
    def save(self, ledger: CashLedgerAggregate) -> None:
        pass
    @abstractmethod
    def find_by_portfolio(self, portfolio_id: str) -> Optional[CashLedgerAggregate]:
        pass

class ValuationRepository(ABC):
    @abstractmethod
    def save(self, valuation: ValuationAggregate) -> None:
        pass
    @abstractmethod
    def find_latest_by_portfolio(self, portfolio_id: str) -> Optional[ValuationAggregate]:
        pass
    @abstractmethod
    def list_all_by_portfolio(self, portfolio_id: str) -> List[ValuationAggregate]:
        pass


class InMemoryPortfolioRepository(PortfolioRepository):
    def __init__(self):
        self._portfolios: Dict[str, PortfolioAggregate] = {}

    def save(self, portfolio: PortfolioAggregate) -> None:
        existing = self._portfolios.get(portfolio.portfolio_id)
        if existing and existing.aggregate_version != portfolio.aggregate_version - 1:
            raise ConcurrencyConflictError("OCC Conflict")
        self._portfolios[portfolio.portfolio_id] = copy.deepcopy(portfolio)

    def find_by_id(self, portfolio_id: str) -> Optional[PortfolioAggregate]:
        item = self._portfolios.get(portfolio_id)
        return copy.deepcopy(item) if item else None


class InMemoryPositionRepository(PositionRepository):
    def __init__(self):
        self._positions: Dict[str, PositionAggregate] = {}

    def save(self, position: PositionAggregate) -> None:
        key = f"{position.portfolio_id}:{position.asset_id}"
        existing = self._positions.get(key)
        if existing and existing.aggregate_version != position.aggregate_version - 1:
            raise ConcurrencyConflictError("OCC Conflict")
        self._positions[key] = copy.deepcopy(position)

    def find_by_portfolio_and_asset(self, portfolio_id: str, asset_id: str) -> Optional[PositionAggregate]:
        item = self._positions.get(f"{portfolio_id}:{asset_id}")
        return copy.deepcopy(item) if item else None

    def list_active_by_portfolio(self, portfolio_id: str) -> List[PositionAggregate]:
        from karsa.portfolio.value_objects import PositionStatus
        return [copy.deepcopy(p) for p in self._positions.values() if p.portfolio_id == portfolio_id and p.status != PositionStatus.CLOSED]


class InMemoryCashLedgerRepository(CashLedgerRepository):
    def __init__(self):
        self._ledgers: Dict[str, CashLedgerAggregate] = {}

    def save(self, ledger: CashLedgerAggregate) -> None:
        existing = self._ledgers.get(ledger.portfolio_id)
        if existing and existing.aggregate_version != ledger.aggregate_version - 1:
            raise ConcurrencyConflictError("OCC Conflict")
        self._ledgers[ledger.portfolio_id] = copy.deepcopy(ledger)

    def find_by_portfolio(self, portfolio_id: str) -> Optional[CashLedgerAggregate]:
        item = self._ledgers.get(portfolio_id)
        return copy.deepcopy(item) if item else None


class InMemoryValuationRepository(ValuationRepository):
    def __init__(self):
        self._valuations: List[ValuationAggregate] = []

    def save(self, valuation: ValuationAggregate) -> None:
        for v in self._valuations:
            if v.valuation_id == valuation.valuation_id:
                raise DatabaseImmutabilityError("Valuations are read-only and immutable")
        self._valuations.append(copy.deepcopy(valuation))

    def find_latest_by_portfolio(self, portfolio_id: str) -> Optional[ValuationAggregate]:
        matches = [v for v in self._valuations if v.portfolio_id == portfolio_id]
        if not matches:
            return None
        return copy.deepcopy(sorted(matches, key=lambda x: x.calculated_at)[-1])

    def list_all_by_portfolio(self, portfolio_id: str) -> List[ValuationAggregate]:
        return [copy.deepcopy(v) for v in self._valuations if v.portfolio_id == portfolio_id]


class FilePortfolioRepository(PortfolioRepository):
    def __init__(self, base_dir: str = ".karsa/portfolio/portfolios"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_path(self, portfolio_id: str) -> str:
        return os.path.join(self.base_dir, f"{portfolio_id}.json")

    def save(self, portfolio: PortfolioAggregate) -> None:
        path = self._get_path(portfolio.portfolio_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            if data.get("aggregate_version", 1) != portfolio.aggregate_version - 1:
                raise ConcurrencyConflictError("OCC Conflict")
        with open(path, "w") as f:
            json.dump({
                "portfolio_id": portfolio.portfolio_id,
                "owner_id": portfolio.owner_id,
                "base_currency": portfolio.base_currency,
                "status": portfolio.status,
                "aggregate_version": portfolio.aggregate_version
            }, f, indent=2)

    def find_by_id(self, portfolio_id: str) -> Optional[PortfolioAggregate]:
        path = self._get_path(portfolio_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return PortfolioAggregate(
            portfolio_id=data["portfolio_id"],
            owner_id=data["owner_id"],
            base_currency=data["base_currency"],
            status=data["status"],
            aggregate_version=data["aggregate_version"]
        )


class FilePositionRepository(PositionRepository):
    def __init__(self, base_dir: str = ".karsa/portfolio/positions"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_path(self, portfolio_id: str, asset_id: str) -> str:
        return os.path.join(self.base_dir, f"{portfolio_id}_{asset_id}.json")

    def save(self, position: PositionAggregate) -> None:
        path = self._get_path(position.portfolio_id, position.asset_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            if data.get("aggregate_version", 1) != position.aggregate_version - 1:
                raise ConcurrencyConflictError("OCC Conflict")
        with open(path, "w") as f:
            from dataclasses import asdict
            json.dump({
                "position_id": position.position_id,
                "portfolio_id": position.portfolio_id,
                "asset_id": position.asset_id,
                "units": str(position.units),
                "average_cost": str(position.average_cost),
                "status": position.status.value,
                "lots": [asdict(lot) for lot in position.lots],
                "aggregate_version": position.aggregate_version
            }, f, indent=2, default=str)

    def find_by_portfolio_and_asset(self, portfolio_id: str, asset_id: str) -> Optional[PositionAggregate]:
        path = self._get_path(portfolio_id, asset_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        from karsa.portfolio.value_objects import PositionStatus, HoldingLot
        pos = PositionAggregate(
            position_id=data["position_id"],
            portfolio_id=data["portfolio_id"],
            asset_id=data["asset_id"],
            units=Decimal(data["units"]),
            average_cost=Decimal(data["average_cost"]),
            status=PositionStatus(data["status"]),
            aggregate_version=data["aggregate_version"]
        )
        for lot in data.get("lots", []):
            pos.lots.append(HoldingLot(
                lot_id=lot["lot_id"],
                acquired_at=datetime.fromisoformat(lot["acquired_at"]),
                units=Decimal(lot["units"]),
                price=Decimal(lot["price"])
            ))
        return pos

    def list_active_by_portfolio(self, portfolio_id: str) -> List[PositionAggregate]:
        active = []
        for filename in os.listdir(self.base_dir):
            if filename.startswith(f"{portfolio_id}_") and filename.endswith(".json"):
                parts = filename[:-5].split("_")
                asset_id = parts[1]
                pos = self.find_by_portfolio_and_asset(portfolio_id, asset_id)
                from karsa.portfolio.value_objects import PositionStatus
                if pos and pos.status != PositionStatus.CLOSED:
                    active.append(pos)
        return active


class FileCashLedgerRepository(CashLedgerRepository):
    def __init__(self, base_dir: str = ".karsa/portfolio/cash"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_path(self, portfolio_id: str) -> str:
        return os.path.join(self.base_dir, f"{portfolio_id}.json")

    def save(self, ledger: CashLedgerAggregate) -> None:
        path = self._get_path(ledger.portfolio_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            if data.get("aggregate_version", 1) != ledger.aggregate_version - 1:
                raise ConcurrencyConflictError("OCC Conflict")
        with open(path, "w") as f:
            json.dump({
                "portfolio_id": ledger.portfolio_id,
                "available_balance": str(ledger.available_balance),
                "held_balance": str(ledger.held_balance),
                "currency": ledger.currency,
                "aggregate_version": ledger.aggregate_version
            }, f, indent=2)

    def find_by_portfolio(self, portfolio_id: str) -> Optional[CashLedgerAggregate]:
        path = self._get_path(portfolio_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return CashLedgerAggregate(
            portfolio_id=data["portfolio_id"],
            available_balance=Decimal(data["available_balance"]),
            held_balance=Decimal(data["held_balance"]),
            currency=data["currency"],
            aggregate_version=data["aggregate_version"]
        )


class FileValuationRepository(ValuationRepository):
    def __init__(self, base_dir: str = ".karsa/portfolio/valuations"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_path(self, valuation_id: str) -> str:
        return os.path.join(self.base_dir, f"{valuation_id}.json")

    def save(self, valuation: ValuationAggregate) -> None:
        path = self._get_path(valuation.valuation_id)
        if os.path.exists(path):
            raise DatabaseImmutabilityError("Valuations are read-only and immutable")
        
        from dataclasses import asdict
        with open(path, "w") as f:
            json.dump({
                "valuation_id": valuation.valuation_id,
                "portfolio_id": valuation.portfolio_id,
                "net_asset_value": str(valuation.net_asset_value),
                "cash_balance": str(valuation.cash_balance),
                "asset_valuations": {k: str(v) for k, v in valuation.asset_valuations.items()},
                "exposures": [asdict(e) for e in valuation.exposures],
                "benchmark_values": {k: str(v) for k, v in valuation.benchmark_values.items()},
                "calculated_at": valuation.calculated_at.isoformat(),
                "aggregate_version": valuation.aggregate_version
            }, f, indent=2, default=str)

    def find_latest_by_portfolio(self, portfolio_id: str) -> Optional[ValuationAggregate]:
        valuations = self.list_all_by_portfolio(portfolio_id)
        if not valuations:
            return None
        return sorted(valuations, key=lambda x: x.calculated_at)[-1]

    def list_all_by_portfolio(self, portfolio_id: str) -> List[ValuationAggregate]:
        from karsa.portfolio.value_objects import AssetExposure
        valuations = []
        for filename in os.listdir(self.base_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.base_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    if data["portfolio_id"] == portfolio_id:
                        exps = [AssetExposure(e["asset_id"], Decimal(e["exposure_pct"]), Decimal(e["exposure_value"])) for e in data["exposures"]]
                        valuations.append(ValuationAggregate(
                            valuation_id=data["valuation_id"],
                            portfolio_id=data["portfolio_id"],
                            net_asset_value=Decimal(data["net_asset_value"]),
                            cash_balance=Decimal(data["cash_balance"]),
                            asset_valuations={k: Decimal(v) for k, v in data["asset_valuations"].items()},
                            exposures=exps,
                            benchmark_values={k: Decimal(v) for k, v in data["benchmark_values"].items()},
                            calculated_at=datetime.fromisoformat(data["calculated_at"]),
                            aggregate_version=data["aggregate_version"]
                        ))
                except Exception:
                    pass
        return valuations
