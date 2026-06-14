from typing import Dict, List, Optional
from decimal import Decimal
from karsa.portfolio.services import PortfolioProjectionService, PortfolioValuationService
from karsa.portfolio.repositories import ValuationRepository, PositionRepository, CashLedgerRepository

class PortfolioAPI:
    def __init__(self, projection_service: PortfolioProjectionService, valuation_service: PortfolioValuationService, valuation_repo: ValuationRepository, position_repo: PositionRepository, cash_repo: CashLedgerRepository):
        self.projection_service = projection_service
        self.valuation_service = valuation_service
        self.valuation_repo = valuation_repo
        self.position_repo = position_repo
        self.cash_repo = cash_repo

    def ingest_fill(self, fill_event: dict) -> dict:
        val = self.projection_service.consume_order_filled(fill_event)
        return {
            "valuation_id": val.valuation_id,
            "net_asset_value": str(val.net_asset_value),
            "cash_balance": str(val.cash_balance)
        }

    def get_valuation(self, portfolio_id: str) -> Optional[dict]:
        val = self.valuation_repo.find_latest_by_portfolio(portfolio_id)
        if not val:
            return None
        return {
            "net_asset_value": str(val.net_asset_value),
            "cash_balance": str(val.cash_balance),
            "exposures": [{
                "asset_id": e.asset_id,
                "exposure_pct": str(e.exposure_pct),
                "exposure_value": str(e.exposure_value)
            } for e in val.exposures]
        }
