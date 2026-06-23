"""Unit tests for Sprint-59: CIO Dashboard.

Tests cover:
- Portfolio state calculator (equity, PnL, exposure)
- CIO Producer (fill processing, mark-to-market, snapshot writing)
- Stale data circuit breaker (FRESH -> STALE -> HALTED)
- WebSocket manager
"""
import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from karsa.cio.dashboard_models import (
    PortfolioState,
    PortfolioSnapshot,
    SectorExposure,
    PnLSnapshot,
    ExposureBreakdown,
    StaleDataState,
    Position,
)
from karsa.cio.dashboard_services import (
    PortfolioStateCalculator,
    StaleDataCircuitBreaker,
    CIOProducer,
)


# ============================================================
# PortfolioStateCalculator Tests
# ============================================================

class TestPortfolioStateCalculator:
    def test_empty_portfolio(self):
        state = PortfolioState(cash_balance=1_000_000)
        snap = PortfolioStateCalculator.compute_snapshot(state)
        assert snap.total_equity == 1_000_000
        assert snap.cash_balance == 1_000_000
        assert snap.position_count == 0

    def test_with_positions(self):
        state = PortfolioState(
            cash_balance=800_000,
            positions={
                "AAPL": Position(symbol="AAPL", quantity=100, avg_entry_price=190, current_price=195, sector="Tech"),
                "XOM": Position(symbol="XOM", quantity=200, avg_entry_price=100, current_price=102, sector="Energy"),
            },
        )
        snap = PortfolioStateCalculator.compute_snapshot(state)
        # equity = 800k + (100*195) + (200*102) = 800k + 19.5k + 20.4k = 839.9k
        assert abs(snap.total_equity - 839_900) < 0.01
        assert snap.position_count == 2

    def test_sector_exposure(self):
        state = PortfolioState(
            cash_balance=500_000,
            positions={
                "AAPL": Position(symbol="AAPL", quantity=100, current_price=200, sector="Tech"),
                "NVDA": Position(symbol="NVDA", quantity=50, current_price=500, sector="Tech"),
                "XOM": Position(symbol="XOM", quantity=200, current_price=100, sector="Energy"),
            },
        )
        exposures = PortfolioStateCalculator.compute_sector_exposures(state)
        by_sector = {e.sector_name: e.net_exposure for e in exposures}
        assert by_sector["Tech"] == 100 * 200 + 50 * 500  # 20k + 25k = 45k
        assert by_sector["Energy"] == 200 * 100  # 20k

    def test_pnl_calculation(self):
        state = PortfolioState(
            cash_balance=900_000,
            realized_pnl=5_000,
            daily_pnl=1_200,
            positions={
                "AAPL": Position(symbol="AAPL", quantity=100, avg_entry_price=190, current_price=195),
            },
        )
        pnl = PortfolioStateCalculator.compute_pnl(state)
        assert pnl.realized_pnl == 5_000
        assert pnl.unrealized_pnl == 100 * (195 - 190)  # 500
        assert pnl.total_pnl == 5_500
        assert pnl.daily_pnl == 1_200

    def test_max_drawdown(self):
        state = PortfolioState(cash_balance=900_000, peak_equity=1_000_000)
        snap = PortfolioStateCalculator.compute_snapshot(state)
        assert abs(snap.max_drawdown_pct - 0.10) < 0.001  # 10% drawdown


# ============================================================
# StaleDataCircuitBreaker Tests
# ============================================================

class TestStaleDataCircuitBreaker:
    def test_initial_state_fresh(self):
        cb = StaleDataCircuitBreaker()
        assert cb.state == StaleDataState.FRESH

    def test_fresh_to_stale(self):
        cb = StaleDataCircuitBreaker(stale_threshold_minutes=5)
        now = datetime(2025, 3, 15, 14, 0, tzinfo=timezone.utc)
        cb.on_bar_received(now)
        # 6 minutes later
        new_state = cb.check_staleness(now + timedelta(minutes=6))
        assert new_state == StaleDataState.STALE
        assert cb.state == StaleDataState.STALE

    def test_stale_to_halted(self):
        cb = StaleDataCircuitBreaker(stale_threshold_minutes=5, halt_threshold_minutes=15)
        now = datetime(2025, 3, 15, 14, 0, tzinfo=timezone.utc)
        cb.on_bar_received(now)
        # 16 minutes later
        cb.check_staleness(now + timedelta(minutes=6))  # -> STALE
        new_state = cb.check_staleness(now + timedelta(minutes=16))  # -> HALTED
        assert new_state == StaleDataState.HALTED

    def test_bar_received_restores_fresh(self):
        cb = StaleDataCircuitBreaker(stale_threshold_minutes=5)
        now = datetime(2025, 3, 15, 14, 0, tzinfo=timezone.utc)
        cb.on_bar_received(now)
        cb.check_staleness(now + timedelta(minutes=6))  # -> STALE
        cb.on_bar_received(now + timedelta(minutes=7))  # bar arrives
        assert cb.state == StaleDataState.FRESH

    def test_manual_resume(self):
        cb = StaleDataCircuitBreaker(stale_threshold_minutes=5, halt_threshold_minutes=15)
        now = datetime(2025, 3, 15, 14, 0, tzinfo=timezone.utc)
        cb.on_bar_received(now)
        cb.check_staleness(now + timedelta(minutes=6))
        cb.check_staleness(now + timedelta(minutes=16))  # -> HALTED
        cb.manual_resume()
        assert cb.state == StaleDataState.FRESH


# ============================================================
# CIOProducer Tests
# ============================================================

class TestCIOProducer:
    def _make_producer(self):
        mock_repo = MagicMock()
        mock_repo.write_snapshot = MagicMock()
        mock_repo.write_sector_exposures = MagicMock()
        mock_publish = AsyncMock()
        mock_ws = AsyncMock()
        return CIOProducer(
            state=PortfolioState(cash_balance=1_000_000),
            snapshot_repo=mock_repo,
            publish_event=mock_publish,
            on_state_update=mock_ws,
        ), mock_repo, mock_ws

    def test_buy_fill_updates_position(self):
        producer, _, _ = self._make_producer()
        async def run():
            await producer.on_fill("AAPL", "BUY", 100, 195.0, sector="Tech")
            state = producer.get_state()
            assert "AAPL" in state.positions
            assert state.positions["AAPL"].quantity == 100
            assert state.positions["AAPL"].avg_entry_price == 195.0
            assert state.cash_balance < 1_000_000  # Cash decreased
        asyncio.run(run())

    def test_sell_fill_realizes_pnl(self):
        producer, _, _ = self._make_producer()
        async def run():
            await producer.on_fill("AAPL", "BUY", 100, 190.0)
            await producer.on_fill("AAPL", "SELL", 100, 200.0)
            state = producer.get_state()
            assert "AAPL" not in state.positions  # Fully closed
            assert state.realized_pnl == 100 * (200 - 190)  # $1000
        asyncio.run(run())

    def test_partial_sell(self):
        producer, _, _ = self._make_producer()
        async def run():
            await producer.on_fill("AAPL", "BUY", 200, 190.0)
            await producer.on_fill("AAPL", "SELL", 100, 200.0)
            state = producer.get_state()
            assert state.positions["AAPL"].quantity == 100
            assert state.realized_pnl == 100 * (200 - 190)
        asyncio.run(run())

    def test_mark_to_market(self):
        producer, _, _ = self._make_producer()
        async def run():
            await producer.on_fill("AAPL", "BUY", 100, 190.0)
            snap = await producer.on_market_bar("AAPL", 195.0)
            assert snap is not None
            # Unrealized PnL = 100 * (195 - 190) = 500
            assert snap.unrealized_pnl == 500
        asyncio.run(run())

    def test_equity_tracking(self):
        producer, _, _ = self._make_producer()
        async def run():
            initial_equity = producer.get_state().total_equity
            await producer.on_fill("AAPL", "BUY", 100, 190.0)
            await producer.on_market_bar("AAPL", 195.0)
            state = producer.get_state()
            # Peak equity should be updated
            assert state.peak_equity >= initial_equity
        asyncio.run(run())

    def test_snapshot_written_on_fill(self):
        producer, mock_repo, mock_ws = self._make_producer()
        async def run():
            await producer.on_fill("AAPL", "BUY", 100, 195.0)
            mock_repo.write_snapshot.assert_called()
            mock_ws.assert_called()
        asyncio.run(run())

    def test_no_position_bar_returns_none(self):
        producer, _, _ = self._make_producer()
        async def run():
            snap = await producer.on_market_bar("UNKNOWN", 100.0)
            assert snap is None
        asyncio.run(run())


# ============================================================
# Integration: Full CIO Pipeline
# ============================================================

class TestCIOIntegration:
    def test_full_fill_bar_snapshot_cycle(self):
        """Simulate: buy AAPL, mark-to-market, verify snapshot."""
        producer, _, _ = CIOProducer(
            state=PortfolioState(cash_balance=1_000_000),
            snapshot_repo=MagicMock(),
            on_state_update=AsyncMock(),
        ), MagicMock(), AsyncMock()

        async def run():
            # Buy — equity stays same (cash → position)
            snap1 = await producer.on_fill("AAPL", "BUY", 500, 195.0, sector="Tech")
            assert snap1.position_count == 1
            assert abs(snap1.total_equity - 1_000_000) < 1.0  # Equity unchanged on buy

            # Price moves up — unrealized gain increases equity
            snap2 = await producer.on_market_bar("AAPL", 200.0)
            assert snap2.total_equity > snap1.total_equity  # Unrealized gain

            # Sell half
            snap3 = await producer.on_fill("AAPL", "SELL", 250, 205.0)
            assert snap3.realized_pnl > 0
            assert snap3.position_count == 1  # Still have 250 shares

        asyncio.run(run())

    def test_multi_position_portfolio(self):
        """Multiple positions across sectors."""
        producer, _, _ = CIOProducer(
            state=PortfolioState(cash_balance=2_000_000),
            snapshot_repo=MagicMock(),
            on_state_update=AsyncMock(),
        ), MagicMock(), AsyncMock()

        async def run():
            await producer.on_fill("AAPL", "BUY", 100, 195.0, sector="Tech")
            await producer.on_fill("XOM", "BUY", 200, 100.0, sector="Energy")
            await producer.on_fill("JPM", "BUY", 150, 180.0, sector="Finance")

            state = producer.get_state()
            assert len(state.positions) == 3

            exposures = producer.get_sector_exposures()
            sectors = {e.sector_name for e in exposures}
            assert sectors == {"Tech", "Energy", "Finance"}

        asyncio.run(run())
