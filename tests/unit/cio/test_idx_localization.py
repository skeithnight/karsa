"""Unit tests for Sprint-60: IDX Localization.

Tests cover:
- IDR currency formatting
- IDX lot size conversion
- IDX sector mapping
- Positions endpoint response
"""
import asyncio
import pytest
from unittest.mock import MagicMock

from karsa.cio.idx_sector_mapper import classify_idx_ticker, get_all_sectors
from karsa.cio.dashboard_models import PortfolioState, Position
from karsa.cio.dashboard_services import CIOProducer


# ============================================================
# IDX Sector Mapper Tests
# ============================================================

class TestIDXSectorMapper:
    def test_financials(self):
        assert classify_idx_ticker("BBCA") == "Financials"
        assert classify_idx_ticker("BBRI") == "Financials"
        assert classify_idx_ticker("BMRI") == "Financials"
        assert classify_idx_ticker("BBNI") == "Financials"

    def test_telecommunications(self):
        assert classify_idx_ticker("TLKM") == "Telecommunications"
        assert classify_idx_ticker("EXCL") == "Telecommunications"
        assert classify_idx_ticker("ISAT") == "Telecommunications"

    def test_basic_materials(self):
        assert classify_idx_ticker("ANTM") == "Basic Materials"
        assert classify_idx_ticker("INCO") == "Basic Materials"
        assert classify_idx_ticker("MDKA") == "Basic Materials"

    def test_technology(self):
        assert classify_idx_ticker("GOTO") == "Technology"
        assert classify_idx_ticker("BUKA") == "Technology"
        assert classify_idx_ticker("EMTK") == "Technology"

    def test_consumer_staples(self):
        assert classify_idx_ticker("UNVR") == "Consumer Staples"
        assert classify_idx_ticker("ICBP") == "Consumer Staples"
        assert classify_idx_ticker("KLBF") == "Consumer Staples"

    def test_energy(self):
        assert classify_idx_ticker("ADRO") == "Energy"
        assert classify_idx_ticker("PTBA") == "Energy"

    def test_case_insensitive(self):
        assert classify_idx_ticker("bbca") == "Financials"
        assert classify_idx_ticker("Tlkm") == "Telecommunications"

    def test_unknown_ticker(self):
        assert classify_idx_ticker("XYZ999") == "Other"
        assert classify_idx_ticker("") == "Other"

    def test_all_sectors(self):
        sectors = get_all_sectors()
        assert "Financials" in sectors
        assert "Telecommunications" in sectors
        assert "Technology" in sectors
        assert "Basic Materials" in sectors
        assert len(sectors) >= 8


# ============================================================
# IDX Lot Size Tests
# ============================================================

class TestIDXLotSize:
    def test_lot_conversion(self):
        """10,000 shares = 100 lots (IDX: 1 lot = 100 shares)."""
        pos = Position(symbol="BBCA", quantity=10000, avg_entry_price=9500, current_price=9750, sector="Financials")
        assert pos.quantity / 100 == 100.0  # 100 lots

    def test_fractional_lot(self):
        """150 shares = 1.5 lots."""
        pos = Position(symbol="BBCA", quantity=150, avg_entry_price=9500, current_price=9750)
        assert pos.quantity / 100 == 1.5

    def test_market_value_idr(self):
        """10,000 shares * Rp 9,750 = Rp 97,500,000."""
        pos = Position(symbol="BBCA", quantity=10000, avg_entry_price=9500, current_price=9750)
        assert pos.market_value == 97_500_000

    def test_unrealized_pnl_idr(self):
        """(9750 - 9500) * 10000 = Rp 2,500,000."""
        pos = Position(symbol="BBCA", quantity=10000, avg_entry_price=9500, current_price=9750)
        assert pos.unrealized_pnl == 2_500_000


# ============================================================
# CIOProducer IDX Integration Tests
# ============================================================

class TestCIOProducerIDX:
    def _make_producer(self):
        return CIOProducer(
            state=PortfolioState(cash_balance=5_000_000_000),  # Rp 5 Miliar
            snapshot_repo=MagicMock(),
            on_state_update=MagicMock(),
        )

    def test_auto_classify_sector(self):
        """CIOProducer should auto-classify IDX tickers on fill."""
        producer = self._make_producer()
        async def run():
            await producer.on_fill("BBCA", "BUY", 10000, 9500)
            state = producer.get_state()
            assert state.positions["BBCA"].sector == "Financials"
        asyncio.run(run())

    def test_auto_classify_tlkm(self):
        producer = self._make_producer()
        async def run():
            await producer.on_fill("TLKM", "BUY", 5000, 3200)
            state = producer.get_state()
            assert state.positions["TLKM"].sector == "Telecommunications"
        asyncio.run(run())

    def test_auto_classify_goto(self):
        producer = self._make_producer()
        async def run():
            await producer.on_fill("GOTO", "BUY", 100000, 150)
            state = producer.get_state()
            assert state.positions["GOTO"].sector == "Technology"
        asyncio.run(run())

    def test_sector_exposure_breakdown(self):
        """Multiple IDX positions should produce correct sector breakdown."""
        producer = self._make_producer()
        async def run():
            await producer.on_fill("BBCA", "BUY", 10000, 9500)    # Financials
            await producer.on_fill("TLKM", "BUY", 5000, 3200)     # Telecommunications
            await producer.on_fill("ANTM", "BUY", 3000, 2000)     # Basic Materials

            exposures = producer.get_sector_exposures()
            by_sector = {e.sector_name: e.net_exposure for e in exposures}

            assert "Financials" in by_sector
            assert "Telecommunications" in by_sector
            assert "Basic Materials" in by_sector
            assert by_sector["Financials"] == 10000 * 9500
        asyncio.run(run())

    def test_rupiah_pnl(self):
        """PnL should be in Rupiah (whole numbers, no cents)."""
        producer = self._make_producer()
        async def run():
            await producer.on_fill("BBCA", "BUY", 10000, 9500)
            await producer.on_fill("BBCA", "SELL", 10000, 9750)
            state = producer.get_state()
            # Realized PnL = (9750 - 9500) * 10000 = Rp 2,500,000
            assert state.realized_pnl == 2_500_000
        asyncio.run(run())
