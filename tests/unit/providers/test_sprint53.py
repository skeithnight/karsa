"""Unit tests for Sprint-53: Resilience, Health & Observability.

Tests cover:
- HealthMonitorService (status tracking, degradation detection)
- FailoverService (fallback selection, connector swap)
- GapFillService (timeframe parsing, retry logic)
- AlertPort contract
- Sprint-53 events
"""
import asyncio
from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from karsa.providers.domain.data_bridge import (
    HealthStatus,
    ProviderType,
    ProviderStatus,
    DataBridgeProvider,
)
from karsa.providers.application.health_monitor import HealthMonitorService
from karsa.providers.application.failover_service import FailoverService
from karsa.providers.application.gap_fill_service import GapFillService
from karsa.providers.application.connector_factory import BaseConnector
from karsa.providers.events.events import (
    ProviderFailoverEvent,
    GapFillCompletedEvent,
)


# ============================================================
# Sprint-53 Event Tests
# ============================================================

class TestSprint53Events:
    def test_failover_event_fields(self):
        event = ProviderFailoverEvent(
            source_provider_id="p1",
            target_provider_id="p2",
            reason="auth_error: bad key",
            source_provider_name="polygon",
            target_provider_name="alpaca",
        )
        assert event.source_provider_id == "p1"
        assert event.target_provider_id == "p2"
        assert event.reason == "auth_error: bad key"

    def test_gap_fill_event_fields(self):
        event = GapFillCompletedEvent(
            provider_id="polygon",
            symbol="AAPL",
            timeframe="1m",
            bars_filled=5,
            gap_start="2026-06-22T14:25:00Z",
            gap_end="2026-06-22T14:30:00Z",
        )
        assert event.bars_filled == 5
        assert event.symbol == "AAPL"


# ============================================================
# HealthMonitorService Tests
# ============================================================

class TestHealthMonitorService:
    def _make_monitor(self):
        mock_health_repo = MagicMock()
        mock_provider_repo = MagicMock()
        degraded_calls = []

        async def on_degraded(provider_id, status, error):
            degraded_calls.append((provider_id, status, error))

        monitor = HealthMonitorService(
            health_repo=mock_health_repo,
            provider_repo=mock_provider_repo,
            check_interval_seconds=1,
            on_degraded=on_degraded,
        )
        return monitor, mock_health_repo, degraded_calls

    def test_initial_status_unknown(self):
        monitor, _, _ = self._make_monitor()
        assert monitor.get_status("p1") == HealthStatus.DISCONNECTED

    def test_register_connector(self):
        monitor, _, _ = self._make_monitor()
        mock_connector = MagicMock(spec=BaseConnector)
        monitor.register_connector("p1", mock_connector)
        # Status is only set after first health check, not on registration
        assert monitor.get_status("p1") == HealthStatus.DISCONNECTED

    def test_unregister_connector(self):
        monitor, _, _ = self._make_monitor()
        mock_connector = MagicMock(spec=BaseConnector)
        monitor.register_connector("p1", mock_connector)
        monitor.unregister_connector("p1")
        assert "p1" not in monitor.get_all_statuses()

    def test_record_health_connected(self):
        async def run():
            monitor, mock_repo, degraded = self._make_monitor()
            await monitor._record_health("p1", HealthStatus.CONNECTED, latency_ms=42)
            assert monitor.get_status("p1") == HealthStatus.CONNECTED
            mock_repo.append.assert_called_once()
            assert len(degraded) == 0  # No degradation
        asyncio.run(run())

    def test_record_health_degraded_triggers_callback(self):
        async def run():
            monitor, mock_repo, degraded = self._make_monitor()
            # First set to connected
            await monitor._record_health("p1", HealthStatus.CONNECTED, latency_ms=42)
            # Then degrade
            await monitor._record_health("p1", HealthStatus.AUTH_ERROR, error_message="bad key")
            assert monitor.get_status("p1") == HealthStatus.AUTH_ERROR
            assert len(degraded) == 1
            assert degraded[0][0] == "p1"
            assert degraded[0][1] == HealthStatus.AUTH_ERROR
        asyncio.run(run())

    def test_same_status_no_duplicate_trigger(self):
        async def run():
            monitor, _, degraded = self._make_monitor()
            await monitor._record_health("p1", HealthStatus.DISCONNECTED)
            await monitor._record_health("p1", HealthStatus.DISCONNECTED)
            # First DISCONNECTED triggers (from initial unknown), second doesn't
            assert len(degraded) == 1
        asyncio.run(run())

    def test_is_running(self):
        monitor, _, _ = self._make_monitor()
        assert not monitor.is_running


# ============================================================
# FailoverService Tests
# ============================================================

class TestFailoverService:
    def _make_service(self):
        mock_repo = MagicMock()
        mock_health_repo = MagicMock()
        mock_cred_service = MagicMock()
        mock_event_bus = MagicMock()
        mock_event_bus.async_publish = AsyncMock()
        mock_alert = AsyncMock()

        mock_cred_service.decrypt.return_value = "decrypted-key"

        svc = FailoverService(
            provider_repo=mock_repo,
            health_repo=mock_health_repo,
            credential_service=mock_cred_service,
            event_bus=mock_event_bus,
            alert_port=mock_alert,
        )
        return svc, mock_repo, mock_cred_service, mock_event_bus, mock_alert

    def test_no_degraded_provider_returns_none(self):
        async def run():
            svc, mock_repo, _, _, _ = self._make_service()
            mock_repo.get.return_value = None
            result = await svc.handle_degradation("p1", HealthStatus.AUTH_ERROR, "bad key", {})
            assert result is None
        asyncio.run(run())

    def test_no_fallback_returns_none(self):
        async def run():
            svc, mock_repo, _, _, mock_alert = self._make_service()
            degraded = DataBridgeProvider("p1", "polygon", ProviderType.MARKET_TICK)
            mock_repo.get.return_value = degraded
            mock_repo.list_by_type.return_value = [degraded]  # Only self, no fallback

            result = await svc.handle_degradation("p1", HealthStatus.AUTH_ERROR, "bad key", {})
            assert result is None
            mock_alert.send_alert.assert_called_once()
        asyncio.run(run())

    def test_successful_failover(self):
        async def run():
            svc, mock_repo, _, mock_bus, mock_alert = self._make_service()
            degraded = DataBridgeProvider("p1", "polygon", ProviderType.MARKET_TICK)
            fallback = DataBridgeProvider("p2", "alpaca", ProviderType.MARKET_TICK)

            mock_repo.get.return_value = degraded
            mock_repo.list_by_type.return_value = [degraded, fallback]
            mock_repo.get_all_configs.return_value = {"symbols": ["AAPL"]}
            mock_repo.get_credential.return_value = MagicMock(ciphertext="enc", nonce="n", key_rotation_version=1)

            # Mock connector creation
            mock_connector = AsyncMock()
            mock_connector.health_check.return_value = True

            active_connectors = {"p1": MagicMock()}
            with patch("karsa.providers.application.failover_service.ConnectorFactory") as mock_factory:
                mock_factory.create.return_value = mock_connector
                result = await svc.handle_degradation(
                    "p1", HealthStatus.AUTH_ERROR, "bad key", active_connectors
                )

            assert result is not None
            assert "p2" in active_connectors
            mock_bus.async_publish.assert_called_once()
            mock_alert.send_alert.assert_called_once()
        asyncio.run(run())


# ============================================================
# GapFillService Tests
# ============================================================

class TestGapFillService:
    def test_parse_timeframe_1m(self):
        svc = GapFillService(event_bus=MagicMock())
        assert svc._parse_timeframe("1m") == (1, "minute")

    def test_parse_timeframe_5m(self):
        svc = GapFillService(event_bus=MagicMock())
        assert svc._parse_timeframe("5m") == (5, "minute")

    def test_parse_timeframe_1h(self):
        svc = GapFillService(event_bus=MagicMock())
        assert svc._parse_timeframe("1h") == (1, "hour")

    def test_parse_timeframe_unknown_defaults_1m(self):
        svc = GapFillService(event_bus=MagicMock())
        assert svc._parse_timeframe("unknown") == (1, "minute")

    def test_max_retries_configurable(self):
        svc = GapFillService(event_bus=MagicMock(), max_retries=5)
        assert svc._max_retries == 5


# ============================================================
# AlertPort Contract Tests
# ============================================================

class TestAlertPort:
    def test_slack_adapter_implements_port(self):
        from karsa.providers.ports import AlertPort
        from karsa.providers.infrastructure.adapters.slack_alert_adapter import SlackAlertAdapter
        adapter = SlackAlertAdapter(webhook_url="https://hooks.slack.com/test")
        assert isinstance(adapter, AlertPort)

    def test_alert_port_is_abstract(self):
        from karsa.providers.ports import AlertPort
        with pytest.raises(TypeError):
            AlertPort()
