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

from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/portfolio", tags=["Portfolio Engine"])

from fastapi import Request

def get_portfolio_api(request: Request) -> PortfolioAPI:
    return request.app.state.container.portfolio_api

@router.get("/test")
def test_endpoint():
    return {"status": "ok", "message": "reached"}

@router.get("/summary")
def get_portfolio_summary(request: Request):
    try:
        api = request.app.state.container.portfolio_api
        val = api.get_valuation("MAIN")
        if not val:
            return {
                "net_asset_value": "0.0",
                "cash_balance": "0.0",
                "exposures": []
            }
        return val
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": tb})

@router.get("/exposure")
def get_portfolio_exposure(request: Request):
    api = request.app.state.container.portfolio_api
    val = api.get_valuation("MAIN")
    if not val:
        return {
            "net_asset_value": "0.0",
            "cash_balance": "0.0",
            "exposures": []
        }
    return val
