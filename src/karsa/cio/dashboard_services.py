"""Sprint-59: CIO Dashboard services.

CIOProducer: Main event consumer — processes fills, bars, theses.
PortfolioStateCalculator: Computes exposures, PnL from in-memory state.
StaleDataCircuitBreaker: Monitors data feed freshness, halts on interruption.
Extends the existing cio/ bounded context.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from karsa.cio.dashboard_models import (
    PortfolioState,
    PortfolioSnapshot,
    SectorExposure,
    PnLSnapshot,
    ExposureBreakdown,
    StaleDataState,
    Position,
)
from karsa.cio.idx_sector_mapper import classify_idx_ticker

logger = logging.getLogger(__name__)

# Stale data thresholds
STALE_THRESHOLD_MINUTES = 5
HALT_THRESHOLD_MINUTES = 15


class PortfolioStateCalculator:
    """Computes portfolio-level metrics from in-memory state.

    Pure computation — no I/O, no side effects.
    """

    @staticmethod
    def compute_snapshot(state: PortfolioState) -> PortfolioSnapshot:
        """Compute a portfolio snapshot from current state."""
        exposure = state.get_exposure()
        return PortfolioSnapshot(
            snapshot_time=datetime.now(timezone.utc),
            total_equity=state.total_equity,
            cash_balance=state.cash_balance,
            gross_exposure=exposure.gross_exposure,
            net_exposure=exposure.net_exposure,
            daily_pnl=state.daily_pnl,
            max_drawdown_pct=state.max_drawdown_pct,
            realized_pnl=state.realized_pnl,
            unrealized_pnl=state.unrealized_pnl,
            position_count=len(state.positions),
        )

    @staticmethod
    def compute_sector_exposures(state: PortfolioState) -> List[SectorExposure]:
        """Compute sector exposure breakdown."""
        exposure = state.get_exposure()
        now = datetime.now(timezone.utc)
        return [
            SectorExposure(
                snapshot_time=now,
                sector_name=sector,
                gross_exposure=abs(value),
                net_exposure=value,
            )
            for sector, value in exposure.by_sector.items()
        ]

    @staticmethod
    def compute_pnl(state: PortfolioState) -> PnLSnapshot:
        """Compute PnL snapshot."""
        return PnLSnapshot(
            realized_pnl=state.realized_pnl,
            unrealized_pnl=state.unrealized_pnl,
            total_pnl=state.total_pnl,
            daily_pnl=state.daily_pnl,
        )


class StaleDataCircuitBreaker:
    """Monitors data feed freshness and halts trading on interruption.

    State machine:
        FRESH  --no_bar_for_5min--> STALE
        STALE  --bar_received--> FRESH
        STALE  --no_bar_for_15min--> HALTED
        HALTED --manual_resume--> FRESH
    """

    def __init__(
        self,
        stale_threshold_minutes: int = STALE_THRESHOLD_MINUTES,
        halt_threshold_minutes: int = HALT_THRESHOLD_MINUTES,
        on_state_change: Optional[Callable] = None,  # async (old_state, new_state) -> None
    ):
        self._stale_threshold = timedelta(minutes=stale_threshold_minutes)
        self._halt_threshold = timedelta(minutes=halt_threshold_minutes)
        self._on_state_change = on_state_change
        self._state = StaleDataState.FRESH
        self._last_bar_time: Optional[datetime] = None

    def on_bar_received(self, bar_timestamp: datetime) -> Optional[StaleDataState]:
        """Process a market bar timestamp. Returns new state if changed."""
        self._last_bar_time = bar_timestamp
        old_state = self._state

        if self._state in (StaleDataState.STALE, StaleDataState.HALTED):
            self._state = StaleDataState.FRESH
            logger.info(f"Data feed restored — state: STALE -> FRESH")
            return self._state

        return None

    def check_staleness(self, now: Optional[datetime] = None) -> Optional[StaleDataState]:
        """Check if data feed is stale. Returns new state if changed."""
        if self._last_bar_time is None:
            return None

        now = now or datetime.now(timezone.utc)
        gap = now - self._last_bar_time
        old_state = self._state

        if self._state == StaleDataState.FRESH and gap > self._stale_threshold:
            self._state = StaleDataState.STALE
            logger.warning(f"Data feed stale for {gap.total_seconds()/60:.1f} min — state: FRESH -> STALE")
            return self._state

        if self._state == StaleDataState.STALE and gap > self._halt_threshold:
            self._state = StaleDataState.HALTED
            logger.critical(f"Data feed halted for {gap.total_seconds()/60:.1f} min — state: STALE -> HALTED")
            return self._state

        return None

    def manual_resume(self) -> None:
        """Manually resume from HALTED state."""
        if self._state == StaleDataState.HALTED:
            self._state = StaleDataState.FRESH
            logger.info("Manual resume — state: HALTED -> FRESH")

    @property
    def state(self) -> StaleDataState:
        return self._state

    @property
    def last_bar_time(self) -> Optional[datetime]:
        return self._last_bar_time


class CIOProducer:
    """Main CIO Dashboard event consumer.

    Processes execution fills (update positions), market bars (mark-to-market),
    and thesis events (track pipeline). Maintains in-memory portfolio state
    and writes snapshots to the repository.
    """

    def __init__(
        self,
        state: Optional[PortfolioState] = None,
        snapshot_repo: Any = None,  # TimescalePortfolioRepository
        publish_event: Optional[Callable] = None,
        on_state_update: Optional[Callable] = None,  # async (snapshot) -> None (for WebSocket)
    ):
        self._state = state or PortfolioState()
        self._repo = snapshot_repo
        self._publish_event = publish_event
        self._on_state_update = on_state_update
        self._calculator = PortfolioStateCalculator()
        self._circuit_breaker = StaleDataCircuitBreaker()
        self._fill_count = 0
        self._bar_count = 0
        self._snapshot_count = 0

    async def on_fill(
        self,
        symbol: str,
        side: str,
        quantity: float,
        fill_price: float,
        commission: float = 0.0,
        sector: str = "",
    ) -> PortfolioSnapshot:
        """Process an execution fill — update positions and cash."""
        now = datetime.now(timezone.utc)
        # Auto-classify sector using IDX mapper if not provided
        if not sector:
            sector = classify_idx_ticker(symbol)

        if side.upper() in ("BUY",):
            # Buying: decrease cash, increase position
            cost = quantity * fill_price + commission
            self._state.cash_balance -= cost

            if symbol in self._state.positions:
                pos = self._state.positions[symbol]
                # Update average entry price
                total_cost = pos.quantity * pos.avg_entry_price + quantity * fill_price
                total_qty = pos.quantity + quantity
                pos.quantity = total_qty
                pos.avg_entry_price = total_cost / total_qty if total_qty > 0 else 0
            else:
                self._state.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_entry_price=fill_price,
                    current_price=fill_price,
                    sector=sector,
                )

        elif side.upper() in ("SELL", "SELL_SHORT"):
            # Selling: increase cash, decrease position
            proceeds = quantity * fill_price - commission
            self._state.cash_balance += proceeds

            if symbol in self._state.positions:
                pos = self._state.positions[symbol]
                # Realize PnL
                realized = quantity * (fill_price - pos.avg_entry_price)
                self._state.realized_pnl += realized
                self._state.daily_pnl += realized

                pos.quantity -= quantity
                if abs(pos.quantity) < 1e-8:
                    del self._state.positions[symbol]
            else:
                # Short selling
                self._state.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=-quantity,
                    avg_entry_price=fill_price,
                    current_price=fill_price,
                    sector=sector,
                )

        self._state.last_fill_timestamp = now
        self._fill_count += 1

        # Update peak equity
        equity = self._state.total_equity
        if equity > self._state.peak_equity:
            self._state.peak_equity = equity

        # Write snapshot
        snapshot = await self._write_snapshot()

        logger.info(
            f"Fill processed: {side} {quantity} {symbol} @ {fill_price}. "
            f"Equity: ${self._state.total_equity:,.2f}"
        )
        return snapshot

    async def on_market_bar(
        self,
        symbol: str,
        close_price: float,
        bar_timestamp: Optional[datetime] = None,
    ) -> Optional[PortfolioSnapshot]:
        """Process a market bar — mark-to-market open positions."""
        if symbol not in self._state.positions:
            return None

        pos = self._state.positions[symbol]
        pos.current_price = close_price
        self._state.last_bar_timestamp = bar_timestamp or datetime.now(timezone.utc)
        self._bar_count += 1

        # Update peak equity
        equity = self._state.total_equity
        if equity > self._state.peak_equity:
            self._state.peak_equity = equity

        # Check circuit breaker
        self._circuit_breaker.on_bar_received(self._state.last_bar_timestamp)

        # Write snapshot
        snapshot = await self._write_snapshot()
        return snapshot

    async def on_thesis_approved(
        self,
        thesis_id: str,
        ticker: str,
        side: str,
    ) -> None:
        """Track thesis pipeline activity."""
        self._state.last_thesis_timestamp = datetime.now(timezone.utc)
        logger.info(f"Thesis tracked: {thesis_id} ({ticker} {side})")

    async def _write_snapshot(self) -> PortfolioSnapshot:
        """Compute and persist a portfolio snapshot."""
        snapshot = self._calculator.compute_snapshot(self._state)
        sector_exposures = self._calculator.compute_sector_exposures(self._state)

        # Persist to repo
        if self._repo:
            try:
                await asyncio.to_thread(self._repo.write_snapshot, snapshot)
                await asyncio.to_thread(self._repo.write_sector_exposures, sector_exposures)
            except Exception as e:
                logger.error(f"Failed to write portfolio snapshot: {e}")

        # Push to WebSocket subscribers
        if self._on_state_update:
            try:
                await self._on_state_update(snapshot)
            except Exception as e:
                logger.error(f"Failed to push state update: {e}")

        self._snapshot_count += 1
        return snapshot

    def check_staleness(self) -> Optional[StaleDataState]:
        """Check if data feed is stale."""
        return self._circuit_breaker.check_staleness()

    def get_state(self) -> PortfolioState:
        """Get current portfolio state (read-only reference)."""
        return self._state

    def get_snapshot(self) -> PortfolioSnapshot:
        """Get current snapshot without persisting."""
        return self._calculator.compute_snapshot(self._state)

    def get_sector_exposures(self) -> List[SectorExposure]:
        """Get current sector exposures."""
        return self._calculator.compute_sector_exposures(self._state)

    @property
    def circuit_breaker(self) -> StaleDataCircuitBreaker:
        return self._circuit_breaker

    @property
    def fill_count(self) -> int:
        return self._fill_count

    @property
    def bar_count(self) -> int:
        return self._bar_count
