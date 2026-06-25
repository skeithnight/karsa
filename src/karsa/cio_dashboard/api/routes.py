"""CIO Dashboard API routes -- Sprint-16/Phase-1.

Endpoints that the CIO dashboard frontend hooks expect.
Reads from investment_workflow repositories AND PostgreSQL
(worker-produced data).
Uses standardized error responses and pagination.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import psycopg
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["CIO Dashboard"])


def _now_iso() -> str:
    """ISO 8601 timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat()


def _get_container(request: Request):
    """Get the application container from app state."""
    return getattr(request.app.state, "container", None)


def _get_investment_container(request: Request):
    """Get the investment workflow container from app state."""
    return getattr(request.app.state, "investment_container", None)


def _get_pg_connection():
    """Get a PostgreSQL connection from environment."""
    url = os.environ.get(
        "POSTGRES_URL",
        "postgresql://karsa:karsa_password@localhost:5432/karsa_db",
    )
    return psycopg.connect(url)


def _query_cio_decisions(limit: int = 50) -> List[Dict[str, Any]]:
    """Query CIO decisions from PostgreSQL (worker-produced data)."""
    try:
        with _get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT decision_id, action_type, target_node_id,
                              decision_payload, created_at
                       FROM cio_decisions
                       ORDER BY created_at DESC
                       LIMIT %s""",
                    (limit,),
                )
                rows = cur.fetchall()
                results = []
                for row in rows:
                    payload = row[3] if row[3] else {}
                    results.append({
                        "decision_id": row[0],
                        "action_type": row[1],
                        "target_node_id": row[2],
                        "allocated_weights": payload.get("allocated_weights", {}),
                        "override_reason": payload.get("override_reason", {}),
                        "created_at": row[4].isoformat() if row[4] else None,
                    })
                return results
    except Exception:
        return []


# --- Portfolio Summary ---
@router.get("/portfolio/summary")
def get_portfolio_summary(request: Request) -> Dict[str, Any]:
    """Portfolio summary for Tier 1 executive view.

    Reads from PostgreSQL portfolio tables (worker-produced data).
    """
    nav = 0.0
    cash_balance = 0.0
    active_holdings = 0

    # Read from PostgreSQL portfolio tables
    try:
        with _get_pg_connection() as conn:
            with conn.cursor() as cur:
                # Get portfolio valuation
                cur.execute(
                    "SELECT net_asset_value, cash_balance FROM portfolio_read_valuations ORDER BY updated_at DESC LIMIT 1"
                )
                row = cur.fetchone()
                if row:
                    nav = float(row[0]) if row[0] else 0.0
                    cash_balance = float(row[1]) if row[1] else 0.0

                # Count active positions (exclude CASH)
                cur.execute(
                    "SELECT COUNT(*) FROM portfolio_read_positions WHERE asset_id != 'CASH'"
                )
                count_row = cur.fetchone()
                if count_row:
                    active_holdings = count_row[0]
    except Exception:
        pass

    # Also count investment workflow decisions
    container = _get_investment_container(request)
    if container and hasattr(container, "decision_repo"):
        decisions = container.decision_repo.list_decisions(page=1, size=10000)
        active_holdings += sum(
            1 for d in decisions
            if hasattr(d, "state") and d.state in ("ACTIVE", "APPROVED")
        )

    nav_display = f"IDR {nav:,.0f}" if nav > 0 else "IDR 0"
    cash_pct = f"{(cash_balance / nav * 100):.1f}%" if nav > 0 else "0%"

    return {
        "nav": nav_display,
        "navChangeWtd": "0%",
        "navChangeYtd": "0%",
        "sharpeRatio": 0.0,
        "maxDrawdownYtd": "0%",
        "activeHoldings": active_holdings,
        "cashPct": cash_pct,
        "last_updated": _now_iso(),
    }


# --- Portfolio Holdings ---
@router.get("/portfolio/holdings")
def get_portfolio_holdings() -> List[Dict[str, Any]]:
    """Portfolio holdings from PostgreSQL (worker-produced data)."""
    try:
        with _get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT asset_id, portfolio_id, quantity, average_cost,
                              market_value, exposure_pct, updated_at
                       FROM portfolio_read_positions
                       WHERE asset_id != 'CASH'
                       ORDER BY asset_id"""
                )
                rows = cur.fetchall()
                return [
                    {
                        "ticker": row[0],
                        "portfolio_id": row[1],
                        "quantity": float(row[2]) if row[2] else 0,
                        "average_cost": float(row[3]) if row[3] else 0,
                        "market_value": float(row[4]) if row[4] else 0,
                        "exposure_pct": float(row[5]) if row[5] else 0,
                        "updated_at": row[6].isoformat() if row[6] else None,
                    }
                    for row in rows
                ]
    except Exception:
        return []


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

    Reads from investment_workflow decisions AND CIO decisions from PostgreSQL.
    """
    results = []

    # 1. Read from investment workflow container (API-produced decisions)
    container = _get_investment_container(request)
    if container and hasattr(container, "decision_repo"):
        decisions = container.decision_repo.list_decisions(page=1, size=100)
        today = datetime.now(timezone.utc).date()

        for d in decisions:
            created = getattr(d, "created_at", None)
            if created and hasattr(created, "date") and created.date() == today:
                results.append({
                    "ticker": d.ticker,
                    "action": _map_state_to_action(d.state),
                    "conviction": d.conviction.level if hasattr(d, "conviction") and d.conviction else None,
                    "targetPrice": str(d.memo.exit_target) if hasattr(d, "memo") and d.memo and d.memo.exit_target else None,
                    "summary": f"Decision for {d.ticker} in state {d.state}",
                    "memoId": None,
                    "source": "workflow",
                })

    # 2. Read from PostgreSQL (worker-produced CIO decisions)
    cio_decisions = _query_cio_decisions(limit=10)
    for d in cio_decisions:
        weights = d.get("allocated_weights", {})
        tickers = list(weights.keys()) if weights else ["N/A"]
        results.append({
            "ticker": ", ".join(tickers[:3]),
            "action": d.get("action_type", "OVERRIDE"),
            "conviction": None,
            "targetPrice": None,
            "summary": f"CIO Decision: {d.get('action_type', 'N/A')} ({d.get('target_node_id', 'N/A')})",
            "memoId": d.get("decision_id"),
            "source": "cio-producer",
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
    container = _get_investment_container(request)
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


# --- Conglomerate Exposure ---
@router.get("/exposures/conglomerates")
def get_conglomerate_exposures(request: Request) -> List[Dict[str, Any]]:
    """Conglomerate exposure heatmap data.

    Groups positions by IDX conglomerate (Prajogo, Sinar Mas, Astra, etc.)
    and computes exposure vs limits from MANDATE.md.
    """
    from karsa.investment_governance.domain.value_objects.idx_conglomerate_mapper import (
        CONGLOMERATE_GROUPS,
        get_conglomerate_group,
    )

    # Get current positions from DB
    positions = []
    try:
        conn = _get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT symbol, market_value_idr FROM positions WHERE market_value_idr > 0")
            positions = cur.fetchall()
        conn.close()
    except Exception:
        pass

    total_portfolio = sum(abs(p[1]) for p in positions) if positions else 1

    # Group by conglomerate
    group_map: Dict[str, Dict] = {}
    for group_name, tickers, limit in CONGLOMERATE_GROUPS:
        group_map[group_name] = {
            "group": group_name,
            "tickers": tickers,
            "total_exposure_idr": 0.0,
            "exposure_pct": 0.0,
            "limit_pct": limit * 100,
            "status": "OK",
        }

    for symbol, value in positions:
        group = get_conglomerate_group(symbol)
        if group and group in group_map:
            group_map[group]["total_exposure_idr"] += abs(value)

    # Compute percentages and status
    for g in group_map.values():
        g["exposure_pct"] = round(g["total_exposure_idr"] / total_portfolio * 100, 2)
        util = g["exposure_pct"] / g["limit_pct"] if g["limit_pct"] > 0 else 0
        if util >= 1.0:
            g["status"] = "BREACH"
        elif util >= 0.8:
            g["status"] = "WARNING"
        else:
            g["status"] = "OK"

    return list(group_map.values())


# --- Equity Curve ---
@router.get("/cio/portfolio/equity-curve")
def get_equity_curve(timeframe: str = "1M") -> list:
    """Portfolio equity curve timeseries for charting."""
    try:
        conn = _get_pg_connection()
        with conn.cursor() as cur:
            # Calculate cutoff based on timeframe
            from datetime import timedelta
            now = datetime.now(timezone.utc)
            cutoffs = {"1D": timedelta(days=1), "1W": timedelta(weeks=1),
                       "1M": timedelta(days=30), "YTD": now.replace(month=1, day=1, hour=0, minute=0, second=0)}
            cutoff = cutoffs.get(timeframe, timedelta(days=30))
            if isinstance(cutoff, timedelta):
                cutoff = now - cutoff

            cur.execute("""
                SELECT snapshot_time, total_equity, daily_pnl
                FROM portfolio_snapshots
                WHERE snapshot_time >= %s
                ORDER BY snapshot_time ASC
            """, (cutoff,))
            rows = cur.fetchall()
        conn.close()

        return [{
            "timestamp": row[0].isoformat() if row[0] else "",
            "totalEquity": float(row[1]) if row[1] else 0,
            "dailyPnl": float(row[2]) if row[2] else 0,
        } for row in rows]
    except Exception:
        return []


# --- Sector Exposures ---
@router.get("/cio/exposures/sectors")
def get_sector_exposures() -> list:
    """Latest sector exposure breakdown."""
    try:
        conn = _get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT sector_name, gross_exposure, net_exposure
                FROM sector_exposures
                WHERE snapshot_time = (SELECT MAX(snapshot_time) FROM sector_exposures)
                ORDER BY sector_name
            """)
            rows = cur.fetchall()
        conn.close()

        return [{
            "sectorName": row[0],
            "grossExposureIdr": float(row[1]) if row[1] else 0,
            "netExposureIdr": float(row[2]) if row[2] else 0,
        } for row in rows]
    except Exception:
        return []


# --- Market Ticker Data ---
@router.get("/market/ticker")
def get_market_ticker() -> list:
    """Market ticker data for the top bar."""
    try:
        conn = _get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT total_equity, daily_pnl
                FROM portfolio_snapshots
                ORDER BY snapshot_time DESC LIMIT 1
            """)
            snap = cur.fetchone()

            cur.execute("""
                SELECT sector_name, net_exposure
                FROM sector_exposures
                WHERE snapshot_time = (SELECT MAX(snapshot_time) FROM sector_exposures)
                ORDER BY net_exposure DESC LIMIT 3
            """)
            sectors = cur.fetchall()
        conn.close()

        tickers = [
            {"label": "IHSG", "value": "5,895.47", "change": "-1.23%", "positive": False},
            {"label": "USD/IDR", "value": "15,892", "change": "-0.12%", "positive": False},
        ]

        for sector_name, exposure in (sectors or []):
            pct = float(exposure) / float(snap[0]) * 100 if snap and snap[0] else 0
            tickers.append({
                "label": sector_name[:8].upper(),
                "value": f"{pct:.1f}%",
                "change": f"{'+' if pct > 5 else ''}{pct - 5:.1f}%",
                "positive": pct > 5,
            })

        return tickers
    except Exception:
        return [
            {"label": "IHSG", "value": "5,895.47", "change": "-1.23%", "positive": False},
            {"label": "USD/IDR", "value": "15,892", "change": "-0.12%", "positive": False},
        ]
