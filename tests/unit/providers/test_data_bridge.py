"""Unit tests for Sprint-51: Data Bridge — Foundation & Schema.

Tests cover:
- CredentialEncryptionService round-trip
- DataBridgeProvider aggregate events
- DataBridgeProviderService CRUD
- ConnectorFactory registry pattern
"""
import os
import base64
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

# Set master key before importing credential service
os.environ["DATA_BRIDGE_MASTER_KEY"] = base64.b64encode(b"0" * 32).decode("ascii")

from karsa.providers.application.credential_service import (
    CredentialEncryptionService,
    MissingMasterKeyError,
    CredentialDecryptionError,
)
from karsa.providers.domain.data_bridge import (
    DataBridgeProvider,
    ProviderType,
    ProviderStatus,
    HealthStatus,
    EncryptedCredential,
    HealthLogEntry,
)
from karsa.providers.application.connector_factory import (
    BaseConnector,
    ConnectorFactory,
    CONNECTOR_REGISTRY,
    register_connector,
)
from karsa.providers.application.data_bridge_services import DataBridgeProviderService


# ============================================================
# CredentialEncryptionService Tests
# ============================================================

class TestCredentialEncryptionService:
    def test_round_trip_encrypt_decrypt(self):
        svc = CredentialEncryptionService()
        plaintext = "sk-test-api-key-12345"
        encrypted = svc.encrypt(plaintext)
        decrypted = svc.decrypt(encrypted)
        assert decrypted == plaintext

    def test_different_nonces_produce_different_ciphertext(self):
        svc = CredentialEncryptionService()
        plaintext = "same-key"
        enc1 = svc.encrypt(plaintext)
        enc2 = svc.encrypt(plaintext)
        assert enc1.ciphertext != enc2.ciphertext  # Different nonces
        assert enc1.nonce != enc2.nonce

    def test_key_rotation_version_preserved(self):
        svc = CredentialEncryptionService()
        encrypted = svc.encrypt("key", key_rotation_version=3)
        assert encrypted.key_rotation_version == 3

    def test_missing_master_key_raises(self):
        with patch.dict(os.environ, {"DATA_BRIDGE_MASTER_KEY": ""}, clear=False):
            with pytest.raises(MissingMasterKeyError):
                CredentialEncryptionService()

    def test_invalid_master_key_length_raises(self):
        short_key = base64.b64encode(b"short").decode("ascii")
        with pytest.raises(MissingMasterKeyError):
            CredentialEncryptionService(master_key_b64=short_key)

    def test_decryption_with_wrong_key_fails(self):
        svc1 = CredentialEncryptionService()
        encrypted = svc1.encrypt("secret")
        # Create service with different key
        other_key = base64.b64encode(b"1" * 32).decode("ascii")
        svc2 = CredentialEncryptionService(master_key_b64=other_key)
        with pytest.raises(CredentialDecryptionError):
            svc2.decrypt(encrypted)

    def test_encrypt_empty_string(self):
        svc = CredentialEncryptionService()
        encrypted = svc.encrypt("")
        decrypted = svc.decrypt(encrypted)
        assert decrypted == ""


# ============================================================
# DataBridgeProvider Aggregate Tests
# ============================================================

class TestDataBridgeProvider:
    def test_create_provider_emits_event(self):
        provider = DataBridgeProvider(
            provider_id="test-001",
            name="polygon",
            ptype=ProviderType.MARKET_TICK,
            priority=10,
        )
        events = provider.pull_domain_events()
        assert len(events) == 1
        assert events[0].provider_id == "test-001"
        assert events[0].name == "polygon"
        assert events[0].ptype == "market_tick"
        assert events[0].priority == 10

    def test_initial_status_is_active(self):
        provider = DataBridgeProvider("p1", "finnhub", ProviderType.NEWS)
        assert provider.status == ProviderStatus.ACTIVE

    def test_pause_emits_status_change_event(self):
        provider = DataBridgeProvider("p1", "finnhub", ProviderType.NEWS)
        provider.pull_domain_events()  # Clear registration event
        provider.pause()
        events = provider.pull_domain_events()
        assert len(events) == 1
        assert events[0].old_status == "active"
        assert events[0].new_status == "paused"
        assert provider.status == ProviderStatus.PAUSED

    def test_resume_emits_status_change_event(self):
        provider = DataBridgeProvider("p1", "finnhub", ProviderType.NEWS)
        provider.pause()
        provider.pull_domain_events()
        provider.resume()
        events = provider.pull_domain_events()
        assert len(events) == 1
        assert events[0].old_status == "paused"
        assert events[0].new_status == "active"

    def test_same_status_no_event(self):
        provider = DataBridgeProvider("p1", "finnhub", ProviderType.NEWS)
        provider.pull_domain_events()
        provider.resume()  # Already active
        events = provider.pull_domain_events()
        assert len(events) == 0

    def test_set_maintenance(self):
        provider = DataBridgeProvider("p1", "finnhub", ProviderType.NEWS)
        provider.set_maintenance()
        assert provider.status == ProviderStatus.MAINTENANCE

    def test_config_changed_emits_event(self):
        provider = DataBridgeProvider("p1", "finnhub", ProviderType.NEWS)
        provider.pull_domain_events()
        provider.notify_config_changed("symbols")
        events = provider.pull_domain_events()
        assert len(events) == 1
        assert events[0].config_key == "symbols"

    def test_health_changed_emits_event(self):
        provider = DataBridgeProvider("p1", "finnhub", ProviderType.NEWS)
        provider.pull_domain_events()
        provider.notify_health_changed(HealthStatus.CONNECTED, latency_ms=42)
        events = provider.pull_domain_events()
        assert len(events) == 1
        assert events[0].status == "connected"
        assert events[0].latency_ms == 42


# ============================================================
# ConnectorFactory Tests
# ============================================================

class TestConnectorFactory:
    def test_register_and_create(self):
        @register_connector("test_provider")
        class TestConnector(BaseConnector):
            async def start(self):
                self._running = True

            async def stop(self):
                self._running = False

            async def health_check(self):
                return True

        connector = ConnectorFactory.create(
            provider_name="test_provider",
            provider_id="p1",
            config={"symbols": ["AAPL"]},
            credentials={"api_key": "test"},
        )
        assert isinstance(connector, TestConnector)
        assert connector.provider_id == "p1"
        assert connector.config == {"symbols": ["AAPL"]}

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="No connector registered"):
            ConnectorFactory.create(
                provider_name="nonexistent",
                provider_id="p1",
                config={},
                credentials={},
            )

    def test_list_registered(self):
        registered = ConnectorFactory.list_registered()
        assert "test_provider" in registered  # From previous test


# ============================================================
# DataBridgeProviderService Tests (mocked repos)
# ============================================================

class TestDataBridgeProviderService:
    def _make_service(self):
        mock_repo = MagicMock()
        mock_health_repo = MagicMock()
        mock_cred_service = MagicMock()
        mock_event_bus = MagicMock()

        mock_cred_service.encrypt.return_value = EncryptedCredential(
            ciphertext="encrypted",
            nonce="nonce",
            key_rotation_version=1,
        )
        mock_cred_service.decrypt.return_value = "decrypted-key"

        svc = DataBridgeProviderService(
            provider_repo=mock_repo,
            health_repo=mock_health_repo,
            credential_service=mock_cred_service,
            event_bus=mock_event_bus,
        )
        return svc, mock_repo, mock_health_repo, mock_cred_service, mock_event_bus

    def test_register_provider(self):
        svc, mock_repo, _, mock_cred, mock_bus = self._make_service()
        provider = svc.register_provider(
            name="polygon",
            ptype="market_tick",
            api_key="sk-test",
            priority=10,
            initial_config={"symbols": ["AAPL", "SPY"]},
        )
        assert provider.name == "polygon"
        assert provider.type == ProviderType.MARKET_TICK
        mock_repo.add.assert_called_once()
        mock_repo.save_credential.assert_called_once()
        mock_repo.save_config.assert_called_once_with(
            provider.provider_id, "symbols", ["AAPL", "SPY"]
        )
        assert mock_bus.publish.call_count >= 1  # At least registration event

    def test_pause_provider(self):
        svc, mock_repo, _, _, mock_bus = self._make_service()
        mock_provider = MagicMock()
        mock_provider.pull_domain_events.return_value = []
        mock_repo.get.return_value = mock_provider

        svc.pause_provider("p1")
        mock_provider.pause.assert_called_once()
        mock_repo.save.assert_called_once()

    def test_pause_unknown_provider_raises(self):
        svc, mock_repo, _, _, _ = self._make_service()
        mock_repo.get.return_value = None
        with pytest.raises(ValueError, match="not found"):
            svc.pause_provider("nonexistent")

    def test_update_config(self):
        svc, mock_repo, _, _, mock_bus = self._make_service()
        mock_provider = MagicMock()
        mock_provider.pull_domain_events.return_value = []
        mock_repo.get.return_value = mock_provider

        svc.update_config("p1", "symbols", ["TSLA"])
        mock_repo.save_config.assert_called_once_with("p1", "symbols", ["TSLA"])
        mock_provider.notify_config_changed.assert_called_once_with("symbols")

    def test_rotate_credentials(self):
        svc, mock_repo, _, mock_cred, mock_bus = self._make_service()
        mock_provider = MagicMock()
        mock_provider.pull_domain_events.return_value = []
        mock_repo.get.return_value = mock_provider
        mock_repo.get_credential.return_value = EncryptedCredential(
            ciphertext="old", nonce="n", key_rotation_version=1,
        )

        svc.rotate_credentials("p1", "new-key", "new-secret")
        assert mock_cred.encrypt.call_count == 2  # key + secret
        mock_repo.save_credential.assert_called_once()

    def test_log_health(self):
        svc, _, mock_health_repo, _, _ = self._make_service()
        svc.log_health("p1", "connected", latency_ms=50)
        mock_health_repo.append.assert_called_once()
