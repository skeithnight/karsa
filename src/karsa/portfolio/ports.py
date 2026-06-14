from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from decimal import Decimal
from karsa.portfolio.models import ValuationAggregate

class ExecutionFilledEventPort(ABC):
    @abstractmethod
    def on_order_filled(self, event_data: dict) -> None:
        pass

class ExecutionRejectedEventPort(ABC):
    @abstractmethod
    def on_order_rejected(self, event_data: dict) -> None:
        pass

class PerformanceValuationSnapshotPort(ABC):
    @abstractmethod
    def get_latest_valuation_snapshot(self, portfolio_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def get_nav_history(self, portfolio_id: str) -> List[dict]:
        pass

class RiskEngineExposureSnapshotPort(ABC):
    @abstractmethod
    def get_current_exposures(self, portfolio_id: str) -> List[dict]:
        pass

    @abstractmethod
    def get_current_holdings(self, portfolio_id: str) -> List[dict]:
        pass


class PortfolioIntegrationPort(ExecutionFilledEventPort, ExecutionRejectedEventPort):
    def __init__(self, projection_service):
        self.projection_service = projection_service
        self.rejected_events = []

    def on_order_filled(self, event_data: dict) -> None:
        self.projection_service.consume_order_filled(event_data)

    def on_order_rejected(self, event_data: dict) -> None:
        self.rejected_events.append(event_data)


class PerformancePortImpl(PerformanceValuationSnapshotPort):
    def __init__(self, valuation_repo):
        self.valuation_repo = valuation_repo

    def get_latest_valuation_snapshot(self, portfolio_id: str) -> Optional[dict]:
        val = self.valuation_repo.find_latest_by_portfolio(portfolio_id)
        if not val:
            return None
        return self._to_dict(val)

    def get_nav_history(self, portfolio_id: str) -> List[dict]:
        valuations = self.valuation_repo.list_all_by_portfolio(portfolio_id)
        return [self._to_dict(v) for v in sorted(valuations, key=lambda x: x.calculated_at)]

    def _to_dict(self, v: ValuationAggregate) -> dict:
        return {
            "valuation_id": v.valuation_id,
            "portfolio_id": v.portfolio_id,
            "net_asset_value": str(v.net_asset_value),
            "cash_balance": str(v.cash_balance),
            "calculated_at": v.calculated_at.isoformat()
        }


class RiskEnginePortImpl(RiskEngineExposureSnapshotPort):
    def __init__(self, valuation_repo, position_repo):
        self.valuation_repo = valuation_repo
        self.position_repo = position_repo

    def get_current_exposures(self, portfolio_id: str) -> List[dict]:
        val = self.valuation_repo.find_latest_by_portfolio(portfolio_id)
        if not val:
            return []
        from dataclasses import asdict
        return [asdict(e) for e in val.exposures]

    def get_current_holdings(self, portfolio_id: str) -> List[dict]:
        positions = self.position_repo.list_active_by_portfolio(portfolio_id)
        return [{
            "asset_id": p.asset_id,
            "units": str(p.units),
            "average_cost": str(p.average_cost)
        } for p in positions]
