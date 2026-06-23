"""Unit tests for Financial Modeling Prep (FMP) Connector — Sprint-61.

Tests cover:
- Registration in CONNECTOR_REGISTRY
- Constructor signature (provider_id, config, credentials)
- set_on_bar callback storage
- stop() sets _running = False
- health_check() returns True when running
- _fetch_quote correct URL and params
- _fetch_quote empty response handling
"""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from karsa.providers.application.connector_factory import CONNECTOR_REGISTRY


# ============================================================
# Registration
# ============================================================

class TestFMPRegistration:
    def test_registered_in_connector_registry(self):
        import karsa.providers.infrastructure.connectors.fmp_connector  # noqa: F401
        assert "fmp" in CONNECTOR_REGISTRY

    def test_registry_class_is_fmp_connector(self):
        from karsa.providers.infrastructure.connectors.fmp_connector import FMPConnector
        assert CONNECTOR_REGISTRY["fmp"] is FMPConnector


# ============================================================
# Constructor
# ============================================================

class TestFMPConstructor:
    def test_constructor_accepts_provider_id_config_credentials(self):
        from karsa.providers.infrastructure.connectors.fmp_connector import FMPConnector
        connector = FMPConnector(
            provider_id="test-fmp-001",
            config={"tickers": ["BBCA.JK"], "poll_interval_seconds": 1800},
            credentials={"api_key": "test-key-123"},
        )
        assert connector.provider_id == "test-fmp-001"
        assert connector._api_key == "test-key-123"
        assert connector._tickers == ["BBCA.JK"]
        assert connector._poll_interval == 1800

    def test_constructor_defaults(self):
        from karsa.providers.infrastructure.connectors.fmp_connector import FMPConnector
        connector = FMPConnector(
            provider_id="test-fmp-002",
            config={},
            credentials={},
        )
        assert connector._api_key == ""
        assert connector._tickers == []
        assert connector._poll_interval == 3600


# ============================================================
# set_on_bar callback
# ============================================================

class TestFMPSetOnBar:
    def test_set_on_bar_stores_callback(self):
        from karsa.providers.infrastructure.connectors.fmp_connector import FMPConnector
        connector = FMPConnector(
            provider_id="test-fmp-003",
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

class TestFMPLifecycle:
    def test_stop_sets_running_false(self):
        from karsa.providers.infrastructure.connectors.fmp_connector import FMPConnector
        connector = FMPConnector(
            provider_id="test-fmp-004",
            config={},
            credentials={},
        )
        connector._running = True

        async def run():
            await connector.stop()
        asyncio.run(run())

        assert connector._running is False

    def test_health_check_returns_true_when_running(self):
        from karsa.providers.infrastructure.connectors.fmp_connector import FMPConnector
        connector = FMPConnector(
            provider_id="test-fmp-005",
            config={},
            credentials={},
        )
        connector._running = True

        async def run():
            return await connector.health_check()
        result = asyncio.run(run())

        assert result is True

    def test_health_check_returns_false_when_stopped(self):
        from karsa.providers.infrastructure.connectors.fmp_connector import FMPConnector
        connector = FMPConnector(
            provider_id="test-fmp-006",
            config={},
            credentials={},
        )
        connector._running = False

        async def run():
            return await connector.health_check()
        result = asyncio.run(run())

        assert result is False


# ============================================================
# _fetch_quote — URL, params, and response handling
# ============================================================

class TestFMPFetchQuote:
    def test_fetch_quote_uses_correct_url_and_params(self):
        from karsa.providers.infrastructure.connectors.fmp_connector import FMPConnector, FMP_BASE_URL
        connector = FMPConnector(
            provider_id="test-fmp-007",
            config={"tickers": ["BBCA.JK"]},
            credentials={"api_key": "my-api-key"},
        )

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "price": 9500.0,
                "open": 9400.0,
                "dayHigh": 9600.0,
                "dayLow": 9350.0,
                "volume": 12000000,
            }
        ]
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        emitted_bars = []

        async def capture_bar(bar):
            emitted_bars.append(bar)

        connector.set_on_bar(capture_bar)

        async def run():
            await connector._fetch_quote(mock_client, "BBCA.JK")
        asyncio.run(run())

        # Verify correct URL and params
        mock_client.get.assert_called_once_with(
            f"{FMP_BASE_URL}/quote/BBCA.JK",
            params={"apikey": "my-api-key"},
        )

        # Verify bar was emitted
        assert len(emitted_bars) == 1
        assert emitted_bars[0].symbol == "BBCA"  # .JK stripped
        assert emitted_bars[0].close == 9500.0
        assert emitted_bars[0].open == 9400.0
        assert emitted_bars[0].high == 9600.0
        assert emitted_bars[0].low == 9350.0
        assert emitted_bars[0].volume == 12000000
        assert emitted_bars[0].source_provider == "fmp"

    def test_fetch_quote_empty_response_no_bar_emitted(self):
        from karsa.providers.infrastructure.connectors.fmp_connector import FMPConnector
        connector = FMPConnector(
            provider_id="test-fmp-008",
            config={"tickers": ["INVALID.JK"]},
            credentials={"api_key": "my-api-key"},
        )

        # FMP returns empty list for unknown tickers
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        emitted_bars = []

        async def capture_bar(bar):
            emitted_bars.append(bar)

        connector.set_on_bar(capture_bar)

        async def run():
            await connector._fetch_quote(mock_client, "INVALID.JK")
        asyncio.run(run())

        # No bar should be emitted for empty response
        assert len(emitted_bars) == 0
