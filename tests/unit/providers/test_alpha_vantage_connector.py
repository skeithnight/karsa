"""Unit tests for Alpha Vantage Connector — Sprint-61.

Tests cover:
- Registration in CONNECTOR_REGISTRY
- Constructor signature (provider_id, config, credentials)
- set_on_bar callback storage
- stop() sets _running = False
- health_check() returns True when running
- .IDX suffix appending
- _fetch_daily correct params including function=TIME_SERIES_DAILY
- _fetch_daily rate limit response handling (Note key)
"""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from karsa.providers.application.connector_factory import CONNECTOR_REGISTRY


# ============================================================
# Registration
# ============================================================

class TestAlphaVantageRegistration:
    def test_registered_in_connector_registry(self):
        import karsa.providers.infrastructure.connectors.alpha_vantage_connector  # noqa: F401
        assert "alpha_vantage" in CONNECTOR_REGISTRY

    def test_registry_class_is_alpha_vantage_connector(self):
        from karsa.providers.infrastructure.connectors.alpha_vantage_connector import AlphaVantageConnector
        assert CONNECTOR_REGISTRY["alpha_vantage"] is AlphaVantageConnector


# ============================================================
# Constructor
# ============================================================

class TestAlphaVantageConstructor:
    def test_constructor_accepts_provider_id_config_credentials(self):
        from karsa.providers.infrastructure.connectors.alpha_vantage_connector import AlphaVantageConnector
        connector = AlphaVantageConnector(
            provider_id="test-av-001",
            config={
                "tickers": ["BBCA", "BBRI"],
                "poll_interval_seconds": 3600,
                "per_ticker_delay_seconds": 5,
            },
            credentials={"api_key": "av-key-123"},
        )
        assert connector.provider_id == "test-av-001"
        assert connector._api_key == "av-key-123"
        assert connector._tickers == ["BBCA", "BBRI"]
        assert connector._poll_interval == 3600
        assert connector._per_ticker_delay == 5

    def test_constructor_defaults(self):
        from karsa.providers.infrastructure.connectors.alpha_vantage_connector import AlphaVantageConnector
        connector = AlphaVantageConnector(
            provider_id="test-av-002",
            config={},
            credentials={},
        )
        assert connector._api_key == ""
        assert connector._tickers == []
        assert connector._poll_interval == 7200
        assert connector._per_ticker_delay == 3


# ============================================================
# set_on_bar callback
# ============================================================

class TestAlphaVantageSetOnBar:
    def test_set_on_bar_stores_callback(self):
        from karsa.providers.infrastructure.connectors.alpha_vantage_connector import AlphaVantageConnector
        connector = AlphaVantageConnector(
            provider_id="test-av-003",
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

class TestAlphaVantageLifecycle:
    def test_stop_sets_running_false(self):
        from karsa.providers.infrastructure.connectors.alpha_vantage_connector import AlphaVantageConnector
        connector = AlphaVantageConnector(
            provider_id="test-av-004",
            config={},
            credentials={},
        )
        connector._running = True

        async def run():
            await connector.stop()
        asyncio.run(run())

        assert connector._running is False

    def test_health_check_returns_true_when_running(self):
        from karsa.providers.infrastructure.connectors.alpha_vantage_connector import AlphaVantageConnector
        connector = AlphaVantageConnector(
            provider_id="test-av-005",
            config={},
            credentials={},
        )
        connector._running = True

        async def run():
            return await connector.health_check()
        result = asyncio.run(run())

        assert result is True

    def test_health_check_returns_false_when_stopped(self):
        from karsa.providers.infrastructure.connectors.alpha_vantage_connector import AlphaVantageConnector
        connector = AlphaVantageConnector(
            provider_id="test-av-006",
            config={},
            credentials={},
        )
        connector._running = False

        async def run():
            return await connector.health_check()
        result = asyncio.run(run())

        assert result is False


# ============================================================
# IDX suffix
# ============================================================

class TestAlphaVantageIdxSuffix:
    def test_idx_suffix_constant(self):
        from karsa.providers.infrastructure.connectors.alpha_vantage_connector import AlphaVantageConnector
        assert AlphaVantageConnector.IDX_SUFFIX == ".IDX"

    def test_suffix_appended_in_fetch_daily_symbol(self):
        """Verify _fetch_daily appends .IDX to the ticker."""
        from karsa.providers.infrastructure.connectors.alpha_vantage_connector import AlphaVantageConnector, AV_BASE_URL
        connector = AlphaVantageConnector(
            provider_id="test-av-007",
            config={"tickers": ["BBCA"]},
            credentials={"api_key": "av-key"},
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Time Series (Daily)": {
                "2026-06-20": {
                    "1. open": "9400.00",
                    "2. high": "9600.00",
                    "3. low": "9350.00",
                    "4. close": "9500.00",
                    "5. volume": "12000000",
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        async def run():
            await connector._fetch_daily(mock_client, "BBCA")
        asyncio.run(run())

        # Verify the call used the .IDX-suffixed symbol
        call_args = mock_client.get.call_args
        assert call_args[0][0] == AV_BASE_URL
        assert call_args[1]["params"]["symbol"] == "BBCA.IDX"


# ============================================================
# _fetch_daily — params and response handling
# ============================================================

class TestAlphaVantageFetchDaily:
    def test_fetch_daily_correct_params(self):
        from karsa.providers.infrastructure.connectors.alpha_vantage_connector import AlphaVantageConnector, AV_BASE_URL
        connector = AlphaVantageConnector(
            provider_id="test-av-008",
            config={"tickers": ["BBRI"]},
            credentials={"api_key": "test-av-key"},
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Time Series (Daily)": {
                "2026-06-20": {
                    "1. open": "4500.00",
                    "2. high": "4600.00",
                    "3. low": "4450.00",
                    "4. close": "4550.00",
                    "5. volume": "8000000",
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        emitted_bars = []

        async def capture_bar(bar):
            emitted_bars.append(bar)

        connector.set_on_bar(capture_bar)

        async def run():
            await connector._fetch_daily(mock_client, "BBRI")
        asyncio.run(run())

        # Verify URL and all params
        mock_client.get.assert_called_once_with(
            AV_BASE_URL,
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": "BBRI.IDX",
                "outputsize": "compact",
                "apikey": "test-av-key",
            },
        )

        # Verify bar content
        assert len(emitted_bars) == 1
        bar = emitted_bars[0]
        assert bar.symbol == "BBRI"  # No suffix in emitted symbol
        assert bar.close == 4550.0
        assert bar.open == 4500.0
        assert bar.high == 4600.0
        assert bar.low == 4450.0
        assert bar.volume == 8000000
        assert bar.source_provider == "alpha_vantage"

    def test_fetch_daily_rate_limit_no_bar_emitted(self):
        from karsa.providers.infrastructure.connectors.alpha_vantage_connector import AlphaVantageConnector
        connector = AlphaVantageConnector(
            provider_id="test-av-009",
            config={"tickers": ["BBCA"]},
            credentials={"api_key": "test-av-key"},
        )

        # Alpha Vantage returns {"Note": "..."} when rate limited
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 25 requests per day."
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        emitted_bars = []

        async def capture_bar(bar):
            emitted_bars.append(bar)

        connector.set_on_bar(capture_bar)

        async def run():
            await connector._fetch_daily(mock_client, "BBCA")
        asyncio.run(run())

        # No bar should be emitted on rate limit
        assert len(emitted_bars) == 0

    def test_fetch_daily_error_message_no_bar_emitted(self):
        from karsa.providers.infrastructure.connectors.alpha_vantage_connector import AlphaVantageConnector
        connector = AlphaVantageConnector(
            provider_id="test-av-010",
            config={"tickers": ["INVALID"]},
            credentials={"api_key": "test-av-key"},
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Error Message": "Invalid API call. Please retry or visit the documentation."
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        emitted_bars = []

        async def capture_bar(bar):
            emitted_bars.append(bar)

        connector.set_on_bar(capture_bar)

        async def run():
            await connector._fetch_daily(mock_client, "INVALID")
        asyncio.run(run())

        assert len(emitted_bars) == 0

    def test_fetch_daily_empty_time_series_no_bar_emitted(self):
        from karsa.providers.infrastructure.connectors.alpha_vantage_connector import AlphaVantageConnector
        connector = AlphaVantageConnector(
            provider_id="test-av-011",
            config={"tickers": ["BBCA"]},
            credentials={"api_key": "test-av-key"},
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Meta Data": {},
            "Time Series (Daily)": {}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        emitted_bars = []

        async def capture_bar(bar):
            emitted_bars.append(bar)

        connector.set_on_bar(capture_bar)

        async def run():
            await connector._fetch_daily(mock_client, "BBCA")
        asyncio.run(run())

        assert len(emitted_bars) == 0
