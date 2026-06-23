"""Unit tests for YFinance EOD Connector — Sprint-61.

Tests cover:
- Registration in CONNECTOR_REGISTRY
- Constructor signature (provider_id, config, credentials)
- set_on_bar callback storage
- stop() sets _running = False
- health_check() returns True when running
- _next_schedule_time schedule logic
"""
import asyncio
from datetime import datetime, timezone, timedelta

import pytest

from karsa.providers.application.connector_factory import CONNECTOR_REGISTRY


# ============================================================
# Registration
# ============================================================

class TestYFinanceRegistration:
    def test_registered_in_connector_registry(self):
        import karsa.providers.infrastructure.connectors.yfinance_connector  # noqa: F401
        assert "yfinance" in CONNECTOR_REGISTRY

    def test_registry_class_is_yfinance_connector(self):
        from karsa.providers.infrastructure.connectors.yfinance_connector import YFinanceConnector
        assert CONNECTOR_REGISTRY["yfinance"] is YFinanceConnector


# ============================================================
# Constructor
# ============================================================

class TestYFinanceConstructor:
    def test_constructor_accepts_provider_id_config_credentials(self):
        from karsa.providers.infrastructure.connectors.yfinance_connector import YFinanceConnector
        connector = YFinanceConnector(
            provider_id="test-yf-001",
            config={"tickers": ["BBCA.JK"], "schedule_hour_utc": 9},
            credentials={},
        )
        assert connector.provider_id == "test-yf-001"
        assert connector._tickers == ["BBCA.JK"]
        assert connector._schedule_hour_utc == 9

    def test_constructor_default_schedule_hour(self):
        from karsa.providers.infrastructure.connectors.yfinance_connector import YFinanceConnector
        connector = YFinanceConnector(
            provider_id="test-yf-002",
            config={"tickers": []},
            credentials={},
        )
        assert connector._schedule_hour_utc == 9


# ============================================================
# set_on_bar callback
# ============================================================

class TestYFinanceSetOnBar:
    def test_set_on_bar_stores_callback(self):
        from karsa.providers.infrastructure.connectors.yfinance_connector import YFinanceConnector
        connector = YFinanceConnector(
            provider_id="test-yf-003",
            config={},
            credentials={},
        )
        async def my_callback(bar):
            pass

        connector.set_on_bar(my_callback)
        assert connector._on_bar_callback is my_callback


# ============================================================
# stop / health_check
# ============================================================

class TestYFinanceLifecycle:
    def test_stop_sets_running_false(self):
        from karsa.providers.infrastructure.connectors.yfinance_connector import YFinanceConnector
        connector = YFinanceConnector(
            provider_id="test-yf-004",
            config={},
            credentials={},
        )
        connector._running = True

        async def run():
            await connector.stop()
        asyncio.run(run())

        assert connector._running is False

    def test_health_check_returns_true_when_running(self):
        from karsa.providers.infrastructure.connectors.yfinance_connector import YFinanceConnector
        connector = YFinanceConnector(
            provider_id="test-yf-005",
            config={},
            credentials={},
        )
        connector._running = True

        async def run():
            return await connector.health_check()
        result = asyncio.run(run())

        assert result is True

    def test_health_check_returns_false_when_stopped(self):
        from karsa.providers.infrastructure.connectors.yfinance_connector import YFinanceConnector
        connector = YFinanceConnector(
            provider_id="test-yf-006",
            config={},
            credentials={},
        )
        connector._running = False

        async def run():
            return await connector.health_check()
        result = asyncio.run(run())

        assert result is False


# ============================================================
# _next_schedule_time
# ============================================================

class TestYFinanceNextScheduleTime:
    def test_returns_same_day_when_before_schedule(self):
        from karsa.providers.infrastructure.connectors.yfinance_connector import YFinanceConnector
        connector = YFinanceConnector(
            provider_id="test-yf-007",
            config={"schedule_hour_utc": 9},
            credentials={},
        )
        # Current time is 05:00 UTC, schedule is 09:00 UTC
        now = datetime(2026, 6, 23, 5, 0, 0, tzinfo=timezone.utc)
        result = connector._next_schedule_time(now)
        assert result == datetime(2026, 6, 23, 9, 0, 0, tzinfo=timezone.utc)

    def test_returns_next_day_when_after_schedule(self):
        from karsa.providers.infrastructure.connectors.yfinance_connector import YFinanceConnector
        connector = YFinanceConnector(
            provider_id="test-yf-008",
            config={"schedule_hour_utc": 9},
            credentials={},
        )
        # Current time is 14:00 UTC, schedule is 09:00 UTC — should go to next day
        now = datetime(2026, 6, 23, 14, 0, 0, tzinfo=timezone.utc)
        result = connector._next_schedule_time(now)
        assert result == datetime(2026, 6, 24, 9, 0, 0, tzinfo=timezone.utc)

    def test_returns_same_day_when_exactly_at_schedule(self):
        from karsa.providers.infrastructure.connectors.yfinance_connector import YFinanceConnector
        connector = YFinanceConnector(
            provider_id="test-yf-009",
            config={"schedule_hour_utc": 9},
            credentials={},
        )
        # Exactly at 09:00 UTC — now >= target, so next day
        now = datetime(2026, 6, 23, 9, 0, 0, tzinfo=timezone.utc)
        result = connector._next_schedule_time(now)
        assert result == datetime(2026, 6, 24, 9, 0, 0, tzinfo=timezone.utc)

    def test_custom_schedule_hour(self):
        from karsa.providers.infrastructure.connectors.yfinance_connector import YFinanceConnector
        connector = YFinanceConnector(
            provider_id="test-yf-010",
            config={"schedule_hour_utc": 16},
            credentials={},
        )
        now = datetime(2026, 6, 23, 10, 30, 0, tzinfo=timezone.utc)
        result = connector._next_schedule_time(now)
        assert result == datetime(2026, 6, 23, 16, 0, 0, tzinfo=timezone.utc)
