"""Sprint-59: CIO Dashboard API — REST endpoints and WebSocket.

FastAPI router serving portfolio summary, equity curve, sector exposures,
and real-time WebSocket updates for the CIO Dashboard frontend.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

from karsa.cio.dashboard_models import (
    PortfolioSnapshot,
    SectorExposure,
    StaleDataState,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cio", tags=["CIO Dashboard"])


# --- Response Models ---

class PortfolioSummaryResponse(BaseModel):
    total_equity: float
    cash_balance: float
    gross_exposure: float
    net_exposure: float
    daily_pnl: float
    realized_pnl: float
    unrealized_pnl: float
    max_drawdown_pct: float
    position_count: int
    stale_data_state: str
    snapshot_time: str


class EquityCurvePoint(BaseModel):
    timestamp: str
    total_equity: float
    daily_pnl: float


class SectorExposureResponse(BaseModel):
    sector_name: str
    gross_exposure: float
    net_exposure: float


class StaleDataResponse(BaseModel):
    state: str
    last_bar_time: Optional[str]


class PositionResponse(BaseModel):
    symbol: str
    quantity_shares: float
    quantity_lots: float
    avg_entry_price: float
    current_price: float
    market_value_idr: float
    unrealized_pnl_idr: float
    unrealized_pnl_pct: float
    sector: str


class PositionsResponse(BaseModel):
    positions: List[PositionResponse]
    total_market_value_idr: float
    total_unrealized_pnl_idr: float


# --- WebSocket Manager ---

class WebSocketManager:
    """Manages WebSocket connections for real-time CIO Dashboard updates."""

    def __init__(self):
        self._connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self._connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self._connections)}")

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        dead = set()
        for ws in self._connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self._connections -= dead

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# Global WebSocket manager
ws_manager = WebSocketManager()


# --- API Factory ---

def create_cio_dashboard_api(
    get_cio_producer: callable,  # () -> CIOProducer
    get_snapshot_repo: callable,  # () -> TimescalePortfolioRepository
) -> APIRouter:
    """Create the CIO Dashboard API router with dependency injection.

    Args:
        get_cio_producer: Callable that returns the CIOProducer instance.
        get_snapshot_repo: Callable that returns the repository instance.

    Returns:
        Configured APIRouter.
    """

    @router.get("/portfolio/summary", response_model=PortfolioSummaryResponse)
    async def get_portfolio_summary():
        """Get latest portfolio summary (equity, cash, exposures, PnL)."""
        producer = get_cio_producer()
        snapshot = producer.get_snapshot()
        stale_state = producer.circuit_breaker.state

        return PortfolioSummaryResponse(
            total_equity=snapshot.total_equity,
            cash_balance=snapshot.cash_balance,
            gross_exposure=snapshot.gross_exposure,
            net_exposure=snapshot.net_exposure,
            daily_pnl=snapshot.daily_pnl,
            realized_pnl=snapshot.realized_pnl,
            unrealized_pnl=snapshot.unrealized_pnl,
            max_drawdown_pct=snapshot.max_drawdown_pct,
            position_count=snapshot.position_count,
            stale_data_state=stale_state.value,
            snapshot_time=snapshot.snapshot_time.isoformat(),
        )

    @router.get("/portfolio/equity-curve", response_model=List[EquityCurvePoint])
    async def get_equity_curve(
        timeframe: str = Query("1D", regex="^(1D|1W|1M|YTD)$"),
    ):
        """Get equity curve time-series for charting."""
        repo = get_snapshot_repo()
        try:
            snapshots = await asyncio.to_thread(repo.get_equity_curve, timeframe)
        except Exception as e:
            logger.error(f"Failed to get equity curve: {e}")
            return []

        return [
            EquityCurvePoint(
                timestamp=s.snapshot_time.isoformat(),
                total_equity=s.total_equity,
                daily_pnl=s.daily_pnl,
            )
            for s in snapshots
        ]

    @router.get("/exposures/sectors", response_model=List[SectorExposureResponse])
    async def get_sector_exposures():
        """Get current sector exposure breakdown."""
        repo = get_snapshot_repo()
        try:
            exposures = await asyncio.to_thread(repo.get_latest_sector_exposures)
        except Exception as e:
            logger.error(f"Failed to get sector exposures: {e}")
            # Fall back to in-memory state
            producer = get_cio_producer()
            exposures = producer.get_sector_exposures()

        return [
            SectorExposureResponse(
                sector_name=exp.sector_name,
                gross_exposure=exp.gross_exposure,
                net_exposure=exp.net_exposure,
            )
            for exp in exposures
        ]

    @router.get("/stale-data", response_model=StaleDataResponse)
    async def get_stale_data_state():
        """Get current stale data circuit breaker state."""
        producer = get_cio_producer()
        cb = producer.circuit_breaker
        return StaleDataResponse(
            state=cb.state.value,
            last_bar_time=cb.last_bar_time.isoformat() if cb.last_bar_time else None,
        )

    @router.get("/positions", response_model=PositionsResponse)
    async def get_positions():
        """Get current open positions with IDX lot sizes and IDR values."""
        producer = get_cio_producer()
        state = producer.get_state()

        positions = []
        total_market_value = 0.0
        total_unrealized_pnl = 0.0

        for symbol, pos in state.positions.items():
            mv = pos.market_value
            upnl = pos.unrealized_pnl
            total_market_value += mv
            total_unrealized_pnl += upnl

            positions.append(PositionResponse(
                symbol=symbol,
                quantity_shares=pos.quantity,
                quantity_lots=round(pos.quantity / 100, 2),  # IDX: 1 lot = 100 shares
                avg_entry_price=pos.avg_entry_price,
                current_price=pos.current_price,
                market_value_idr=mv,
                unrealized_pnl_idr=upnl,
                unrealized_pnl_pct=pos.unrealized_pnl_pct * 100,
                sector=pos.sector,
            ))

        return PositionsResponse(
            positions=positions,
            total_market_value_idr=total_market_value,
            total_unrealized_pnl_idr=total_unrealized_pnl,
        )

    @router.websocket("/ws/live")
    async def websocket_live(websocket: WebSocket):
        """WebSocket endpoint for real-time CIO Dashboard updates.

        Pushes portfolio updates on fill and mark-to-market events.
        """
        await ws_manager.connect(websocket)
        try:
            # Send initial state on connect
            producer = get_cio_producer()
            snapshot = producer.get_snapshot()
            await websocket.send_json({
                "type": "initial_state",
                "data": {
                    "total_equity": snapshot.total_equity,
                    "cash_balance": snapshot.cash_balance,
                    "daily_pnl": snapshot.daily_pnl,
                    "max_drawdown_pct": snapshot.max_drawdown_pct,
                    "position_count": snapshot.position_count,
                    "stale_data_state": producer.circuit_breaker.state.value,
                },
            })

            # Keep connection alive, handle client messages
            while True:
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(), timeout=30.0
                    )
                    # Client can request specific data
                    msg = json.loads(data)
                    if msg.get("type") == "request_snapshot":
                        snap = producer.get_snapshot()
                        await websocket.send_json({
                            "type": "snapshot",
                            "data": {
                                "total_equity": snap.total_equity,
                                "cash_balance": snap.cash_balance,
                                "daily_pnl": snap.daily_pnl,
                            },
                        })
                except asyncio.TimeoutError:
                    # Send heartbeat
                    await websocket.send_json({"type": "heartbeat"})
                except json.JSONDecodeError:
                    pass

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            ws_manager.disconnect(websocket)

    return router
