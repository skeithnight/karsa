"""CIO Dashboard API routes -- Sprint-16/Phase-1.

Endpoints that the CIO dashboard frontend hooks expect.
Reads from investment_workflow and capability_engine repositories.
Uses standardized error responses and pagination.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["CIO Dashboard"])


def _now_iso() -> str:
    """ISO 8601 timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat()


def _get_container(request: Request):
    """Get the application container from app state."""
    return getattr(request.app.state, "container", None)


# --- Portfolio Summary ---
@router.get("/portfolio/summary")
def get_portfolio_summary(request: Request) -> Dict[str, Any]:
    """Portfolio summary for Tier 1 executive view.

    Reads from investment_workflow decisions to compute active holdings count.
    """
    container = _get_container(request)
    active_holdings = 0
    if container and hasattr(container, "decision_repo"):
        decisions = container.decision_repo.list_decisions(page=1, size=10000)
        active_holdings = sum(
            1 for d in decisions
            if hasattr(d, "state") and d.state in ("ACTIVE", "APPROVED")
        )

    return {
        "nav": "IDR 0",
        "navChangeWtd": "0%",
        "navChangeYtd": "0%",
        "sharpeRatio": 0.0,
        "maxDrawdownYtd": "0%",
        "activeHoldings": active_holdings,
        "cashPct": "0%",
        "last_updated": _now_iso(),
    }


# --- Risk Traffic Light ---
@router.get("/risk/traffic-light")
def get_risk_traffic_light() -> List[Dict[str, Any]]:
    """Risk metrics for Tier 1 traffic light.

    Returns standard risk metrics with mandate limits from MANDATE.md.
    """
    return [
        {"metric": "Volatility", "current": "0%", "limit": "22%", "utilizationPct": 0, "status": "GREEN"},
        {"metric": "Beta", "current": "1.0", "limit": "0.8-1.3", "utilizationPct": 50, "status": "GREEN"},
        {"metric": "Concentration", "current": "0%", "limit": "60%", "utilizationPct": 0, "status": "GREEN"},
        {"metric": "Sector Max", "current": "0%", "limit": "30%", "utilizationPct": 0, "status": "GREEN"},
        {"metric": "Liquidity", "current": "100%", "limit": "5 days", "utilizationPct": 0, "status": "GREEN"},
        {"metric": "Drawdown", "current": "0%", "limit": "15%", "utilizationPct": 0, "status": "GREEN"},
    ]


# --- Today's Decisions ---
@router.get("/decisions/today")
def get_today_decisions(request: Request) -> List[Dict[str, Any]]:
    """Today's investment decisions for Tier 1.

    Reads from investment_workflow decisions.
    """
    container = _get_container(request)
    if not container or not hasattr(container, "decision_repo"):
        return []

    decisions = container.decision_repo.list_decisions(page=1, size=100)
    today = datetime.now(timezone.utc).date()

    results = []
    for d in decisions:
        created = getattr(d, "created_at", None)
        if created and hasattr(created, "date") and created.date() == today:
            results.append({
                "ticker": d.ticker,
                "action": _map_state_to_action(d.state),
                "conviction": getattr(d, "conviction", {}).get("level") if hasattr(d, "conviction") and d.conviction else None,
                "targetPrice": None,
                "summary": f"Decision for {d.ticker} in state {d.state}",
                "memoId": None,
            })

    return results


def _map_state_to_action(state: str) -> str:
    """Map decision state to display action."""
    mapping = {
        "APPROVED": "BUY",
        "REJECTED": "PASS",
        "PROPOSED": "MONITOR",
        "ANALYZING": "MONITOR",
        "DEBATING": "MONITOR",
        "DECIDING": "MONITOR",
        "RISK_REVIEW": "ALERT",
        "COMMITTEE_REVIEW": "ALERT",
        "REVISED": "MONITOR",
        "SUSPENDED": "ALERT",
    }
    return mapping.get(state, "MONITOR")


# --- Stock Decision ---
@router.get("/decisions/{ticker}/latest")
def get_stock_decision(ticker: str, request: Request) -> Dict[str, Any]:
    """Latest decision for a specific stock.

    Reads from investment_workflow decisions.
    """
    container = _get_container(request)
    if not container or not hasattr(container, "decision_repo"):
        return _empty_decision(ticker)

    decisions = container.decision_repo.list_decisions(page=1, size=10000)
    ticker_decisions = [d for d in decisions if d.ticker == ticker]

    if not ticker_decisions:
        return _empty_decision(ticker)

    # Get the most recent decision
    latest = max(ticker_decisions, key=lambda d: getattr(d, "created_at", datetime.min))

    return {
        "ticker": ticker,
        "status": _map_state_to_decision(latest.state),
        "currentPrice": "",
        "entryPrice": str(latest.memo.entry_price) if latest.memo and latest.memo.entry_price else None,
        "targetPrice": str(latest.memo.exit_target) if latest.memo and latest.memo.exit_target else None,
        "stopLoss": str(latest.memo.stop_loss) if latest.memo and latest.memo.stop_loss else None,
        "positionSizePct": str(latest.memo.position_size_pct) if latest.memo and latest.memo.position_size_pct else None,
        "convictionLevel": latest.conviction.level if latest.conviction else None,
        "convictionScore": latest.conviction.numeric_score if latest.conviction else None,
        "analystScores": {o.analyst_type: o.score for o in latest.analyst_outputs} if latest.analyst_outputs else {},
        "returnSinceEntry": None,
        "nextCatalyst": None,
        "riskFactors": latest.memo.risks if latest.memo and latest.memo.risks else [],
    }


def _empty_decision(ticker: str) -> Dict[str, Any]:
    return {
        "ticker": ticker,
        "status": "PASS",
        "currentPrice": "",
        "entryPrice": None,
        "targetPrice": None,
        "stopLoss": None,
        "positionSizePct": None,
        "convictionLevel": None,
        "convictionScore": None,
        "analystScores": {},
        "returnSinceEntry": None,
        "nextCatalyst": None,
        "riskFactors": [],
    }


def _map_state_to_decision(state: str) -> str:
    """Map decision state to stock decision status."""
    mapping = {
        "APPROVED": "BUY",
        "REJECTED": "PASS",
        "REVISED": "HOLD",
    }
    return mapping.get(state, "PASS")


# --- Risk Heatmap ---
@router.get("/risk/sector-allocation")
def get_sector_allocation() -> List[Dict[str, Any]]:
    """Sector allocation for risk heatmap.

    Returns standard sector limits from MANDATE.md.
    """
    return [
        {"sector": "Finance", "currentPct": 0.0, "limitPct": 30.0, "utilizationPct": 0, "status": "GREEN"},
        {"sector": "Energy", "currentPct": 0.0, "limitPct": 20.0, "utilizationPct": 0, "status": "GREEN"},
        {"sector": "Consumer", "currentPct": 0.0, "limitPct": 25.0, "utilizationPct": 0, "status": "GREEN"},
        {"sector": "Technology", "currentPct": 0.0, "limitPct": 15.0, "utilizationPct": 0, "status": "GREEN"},
        {"sector": "Infrastructure", "currentPct": 0.0, "limitPct": 15.0, "utilizationPct": 0, "status": "GREEN"},
    ]


# --- Performance Attribution ---
@router.get("/performance/attribution")
def get_performance_attribution(period: str = "YTD") -> Dict[str, Any]:
    """Performance attribution breakdown.

    Returns empty attribution structure (no positions yet).
    """
    return {
        "period": period,
        "selectionPct": 0.0,
        "allocationPct": 0.0,
        "betaPct": 0.0,
        "residualPct": 0.0,
        "totalReturnPct": 0.0,
        "winRate": 0.0,
        "modelAccuracy": 0.0,
    }
