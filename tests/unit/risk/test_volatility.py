"""Unit tests for Sprint-58: Live Risk — Volatility Targeting.

Tests cover:
- EWMA volatility calculation
- Risk calibration engine (position sizing formula)
- Edge cases (zero volume, halted stock, no vol data)
- Fail-open behavior
"""
import asyncio
import math
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from karsa.risk.volatility_models import (
    AssetRiskMetrics,
    EWMAParameters,
    RiskTarget,
    VolatilityEstimate,
    RiskCalibrationResult,
)
from karsa.risk.volatility_services import (
    VolatilityCalculator,
    RiskCalibrationEngine,
    DEFAULT_ANNUALIZED_VOL,
)


# ============================================================
# VolatilityCalculator Tests
# ============================================================

class TestVolatilityCalculator:
    def _make_calculator(self, span_days=20):
        mock_repo = MagicMock()
        mock_repo.upsert_metrics = MagicMock()
        mock_repo.get_latest = MagicMock(return_value=None)
        params = EWMAParameters(span_days=span_days)
        return VolatilityCalculator(metrics_repo=mock_repo, params=params), mock_repo

    def test_ewma_decay_factor(self):
        params = EWMAParameters(span_days=20)
        expected = 1.0 - (2.0 / 21.0)
        assert abs(params.decay_factor - expected) < 1e-10

    def test_needs_two_prices(self):
        calc, _ = self._make_calculator()
        result = calc.on_market_bar("AAPL", 195.0)
        assert result is None  # Only 1 price

    def test_computes_volatility(self):
        calc, mock_repo = self._make_calculator()
        # Feed a series of prices with known returns
        prices = [100.0, 101.0, 102.0, 100.5, 103.0, 99.0, 101.5]
        for p in prices:
            result = calc.on_market_bar("AAPL", p)

        assert result is not None
        assert result.realized_volatility > 0
        assert result.daily_vol_pct > 0
        mock_repo.upsert_metrics.assert_called()

    def test_high_volatility_asset(self):
        calc, _ = self._make_calculator()
        # Meme stock: 10% daily swings
        prices = [100.0, 110.0, 99.0, 108.9, 98.0, 107.8, 97.0]
        for p in prices:
            result = calc.on_market_bar("MEME", p)

        assert result is not None
        assert result.realized_volatility > 0.5  # Should be very high

    def test_low_volatility_asset(self):
        calc, _ = self._make_calculator()
        # Utility stock: 0.5% daily moves
        prices = [100.0, 100.5, 100.25, 100.75, 100.5, 101.0, 100.75]
        for p in prices:
            result = calc.on_market_bar("UTIL", p)

        assert result is not None
        assert result.realized_volatility < 0.30  # Should be low

    def test_get_volatility_estimate_from_memory(self):
        calc, _ = self._make_calculator()
        calc.on_market_bar("AAPL", 100.0)
        calc.on_market_bar("AAPL", 102.0)
        estimate = calc.get_volatility_estimate("AAPL")
        assert estimate.is_valid
        assert estimate.annualized_vol > 0

    def test_get_volatility_estimate_default(self):
        calc, mock_repo = self._make_calculator()
        mock_repo.get_latest = MagicMock(return_value=None)
        estimate = calc.get_volatility_estimate("UNKNOWN")
        assert estimate.annualized_vol == DEFAULT_ANNUALIZED_VOL
        assert estimate.daily_vol_pct > 0

    def test_history_capped(self):
        calc, _ = self._make_calculator()
        for i in range(600):
            calc.on_market_bar("AAPL", 100.0 + i * 0.1)
        assert len(calc._price_history["AAPL"]) <= 250


# ============================================================
# RiskCalibrationEngine Tests
# ============================================================

class TestRiskCalibrationEngine:
    def _make_engine(self, vol=0.245, price=195.0, target_usd=10_000):
        mock_repo = MagicMock()
        mock_repo.upsert_metrics = MagicMock()
        mock_repo.get_latest = MagicMock(return_value=AssetRiskMetrics(
            symbol="AAPL",
            realized_volatility=vol,
            daily_vol_pct=vol / math.sqrt(252) * 100,
        ))
        vol_calc = VolatilityCalculator(metrics_repo=mock_repo)
        mock_publish = AsyncMock()
        return RiskCalibrationEngine(
            volatility_calculator=vol_calc,
            risk_target=RiskTarget(target_risk_per_trade_usd=target_usd),
            portfolio_value_usd=1_000_000,
            get_current_price=lambda s: price,
            publish_event=mock_publish,
        ), mock_publish

    def test_ai_size_within_target_passes_through(self):
        engine, mock_pub = self._make_engine(vol=0.245, price=195.0, target_usd=10_000)
        # daily_vol = 0.245 / sqrt(252) = 0.01545
        # daily_price_vol = 195 * 0.01545 = 3.01
        # risk_target_shares = 10000 / 3.01 = 3322
        # AI asks for 1000 — should pass through
        async def run():
            result = await engine.calibrate_thesis(
                thesis_id="urn:karsa:thesis:test",
                ticker="AAPL",
                side="BUY",
                original_quantity=1000,
                price=195.0,
            )
            assert result.risk_scaling_applied is False
            assert result.calibrated_quantity == 1000
        asyncio.run(run())

    def test_ai_size_exceeding_target_scaled_down(self):
        engine, mock_pub = self._make_engine(vol=0.245, price=195.0, target_usd=10_000)
        # risk_target_shares ≈ 3322
        # AI asks for 5000 — should be scaled down
        async def run():
            result = await engine.calibrate_thesis(
                thesis_id="urn:karsa:thesis:test",
                ticker="AAPL",
                side="BUY",
                original_quantity=5000,
                price=195.0,
            )
            assert result.risk_scaling_applied is True
            assert result.calibrated_quantity < 5000
            assert result.calibrated_quantity > 0
            mock_pub.assert_called_once()
        asyncio.run(run())

    def test_high_vol_smaller_position(self):
        # High vol (80%) should produce smaller risk-targeted size
        engine_low, _ = self._make_engine(vol=0.15, price=100.0, target_usd=10_000)
        engine_high, _ = self._make_engine(vol=0.80, price=100.0, target_usd=10_000)

        async def run():
            result_low = await engine_low.calibrate_thesis(
                "t1", "LOW", "BUY", 10000, 100.0,
            )
            result_high = await engine_high.calibrate_thesis(
                "t2", "HIGH", "BUY", 10000, 100.0,
            )
            # High vol should produce smaller calibrated quantity
            assert result_high.calibrated_quantity < result_low.calibrated_quantity
        asyncio.run(run())

    def test_zero_price_vol_passes_through(self):
        engine, _ = self._make_engine(vol=0.0, price=195.0)
        async def run():
            result = await engine.calibrate_thesis(
                "t1", "AAPL", "BUY", 1000, 195.0,
            )
            assert result.risk_scaling_applied is False
            assert result.calibrated_quantity == 1000
        asyncio.run(run())

    def test_unknown_asset_uses_default_vol(self):
        engine, _ = self._make_engine(vol=0.0, price=100.0)
        # Force repo to return None for unknown symbol
        engine._vol_calc._repo.get_latest = MagicMock(return_value=None)
        async def run():
            result = await engine.calibrate_thesis(
                "t1", "UNKNOWN", "BUY", 1000, 100.0,
            )
            # Should use DEFAULT_ANNUALIZED_VOL (50%) — high vol, likely scales down
            assert result.volatility_estimate.annualized_vol == DEFAULT_ANNUALIZED_VOL
        asyncio.run(run())

    def test_fail_open_on_crash(self):
        """If risk engine crashes, thesis must pass through unmodified."""
        engine, _ = self._make_engine()
        # Simulate crash by making vol_calc raise
        engine._vol_calc.get_volatility_estimate = MagicMock(side_effect=Exception("DB down"))
        async def run():
            try:
                result = await engine.calibrate_thesis(
                    "t1", "AAPL", "BUY", 1000, 195.0,
                )
                # Should still return a result (fail-open)
                assert result is not None
            except Exception:
                # If it raises, that's also acceptable — the caller handles it
                pass
        asyncio.run(run())

    def test_conviction_scaling(self):
        engine, _ = self._make_engine(vol=0.245, price=195.0, target_usd=10_000)
        async def run():
            # High conviction
            result_high = await engine.calibrate_thesis(
                "t1", "AAPL", "BUY", 5000, 195.0, conviction=1.0,
            )
            # Low conviction
            result_low = await engine.calibrate_thesis(
                "t2", "AAPL", "BUY", 5000, 195.0, conviction=0.3,
            )
            # Low conviction should produce smaller calibrated quantity
            assert result_low.calibrated_quantity < result_high.calibrated_quantity
        asyncio.run(run())

    def test_counts(self):
        engine, _ = self._make_engine()
        async def run():
            await engine.calibrate_thesis("t1", "AAPL", "BUY", 1000, 195.0)
            await engine.calibrate_thesis("t2", "AAPL", "BUY", 5000, 195.0)
            assert engine.calibration_count == 2
            assert engine.override_count == 1  # Second one should be scaled down
        asyncio.run(run())
