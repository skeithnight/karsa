"""Unit tests for LLM Pool configuration service."""
import os
import base64
import pytest
from unittest.mock import MagicMock

os.environ["DATA_BRIDGE_MASTER_KEY"] = base64.b64encode(b"0" * 32).decode("ascii")

from karsa.providers.application.credential_service import CredentialEncryptionService
from karsa.llm.domain.config_models import (
    LLMProvider,
    LLMProviderStatus,
    LLMCredential,
    LLMModelGroupEntry,
    LLMRouterSettings,
    RoutingStrategy,
)
from karsa.llm.application.config_service import LLMConfigService


class TestLLMConfigService:
    def _make_service(self):
        mock_repo = MagicMock()
        mock_cred = CredentialEncryptionService()
        mock_bus = MagicMock()
        svc = LLMConfigService(
            config_repo=mock_repo,
            credential_service=mock_cred,
            event_bus=mock_bus,
        )
        return svc, mock_repo, mock_cred, mock_bus

    def test_register_provider(self):
        svc, mock_repo, mock_cred, mock_bus = self._make_service()
        provider = svc.register_provider(
            name="openai",
            api_key="sk-test-key",
            base_url="https://api.openai.com/v1",
            priority=10,
        )
        assert provider.name == "openai"
        assert provider.base_url == "https://api.openai.com/v1"
        mock_repo.add_provider.assert_called_once()
        mock_repo.save_credential.assert_called_once()
        assert mock_bus.publish.call_count >= 1

    def test_rotate_api_key(self):
        svc, mock_repo, mock_cred, mock_bus = self._make_service()
        mock_repo.get_credential.return_value = LLMCredential(
            ciphertext="old", nonce="n", key_rotation_version=1,
        )
        svc.rotate_api_key("p1", "new-key")
        mock_repo.save_credential.assert_called_once()
        saved_cred = mock_repo.save_credential.call_args[0][1]
        assert saved_cred.key_rotation_version == 2

    def test_get_decrypted_key(self):
        svc, mock_repo, mock_cred, mock_bus = self._make_service()
        encrypted = mock_cred.encrypt("sk-test-key")
        mock_repo.get_credential.return_value = encrypted
        result = svc.get_decrypted_key("p1")
        assert result == "sk-test-key"

    def test_add_model_to_group(self):
        svc, mock_repo, mock_cred, mock_bus = self._make_service()
        mock_repo.get_provider_by_name.return_value = LLMProvider(
            provider_id="p1", name="openai", priority=10,
        )
        svc.add_model_to_group(
            group_name="karsa-reasoning",
            model_name="gpt-4o",
            provider_name="openai",
            priority=10,
            temperature=0.2,
        )
        mock_repo.add_model_group.assert_called_once()
        call_args = mock_repo.add_model_group.call_args
        assert call_args[0][0] == "karsa-reasoning"
        assert call_args[0][1].model_name == "gpt-4o"

    def test_add_model_unknown_provider_raises(self):
        svc, mock_repo, mock_cred, mock_bus = self._make_service()
        mock_repo.get_provider_by_name.return_value = None
        with pytest.raises(ValueError, match="not found"):
            svc.add_model_to_group("karsa-reasoning", "gpt-4o", "nonexistent")

    def test_update_router_settings(self):
        svc, mock_repo, mock_cred, mock_bus = self._make_service()
        svc.update_router_settings(
            group_name="karsa-reasoning",
            routing_strategy=RoutingStrategy.LATENCY.value,
            num_retries=5,
            timeout_seconds=30,
        )
        mock_repo.save_router_settings.assert_called_once()
        settings = mock_repo.save_router_settings.call_args[0][0]
        assert settings.group_name == "karsa-reasoning"
        assert settings.num_retries == 5
        assert settings.timeout_seconds == 30

    def test_set_system_config(self):
        svc, mock_repo, mock_cred, mock_bus = self._make_service()
        svc.set_system_config("risk", "max_position_pct", 0.05, "Max position as % of portfolio")
        mock_repo.save_system_config.assert_called_once()

    def test_get_system_config(self):
        svc, mock_repo, mock_cred, mock_bus = self._make_service()
        mock_repo.get_system_config.return_value = 0.05
        result = svc.get_system_config("risk", "max_position_pct")
        assert result == 0.05


class TestLLMDomainModels:
    def test_provider_create_emits_event(self):
        provider = LLMProvider(provider_id="p1", name="openai", priority=10)
        events = provider.pull_domain_events()
        assert len(events) == 1
        assert events[0].name == "openai"

    def test_provider_initial_status_active(self):
        provider = LLMProvider(provider_id="p1", name="openai")
        assert provider.status == LLMProviderStatus.ACTIVE

    def test_provider_pause(self):
        provider = LLMProvider(provider_id="p1", name="openai")
        provider.pause()
        assert provider.status == LLMProviderStatus.PAUSED

    def test_provider_resume(self):
        provider = LLMProvider(provider_id="p1", name="openai")
        provider.pause()
        provider.pull_domain_events()
        provider.resume()
        assert provider.status == LLMProviderStatus.ACTIVE
        events = provider.pull_domain_events()
        assert len(events) == 1
        assert events[0].new_status == "active"

    def test_same_status_no_event(self):
        provider = LLMProvider(provider_id="p1", name="openai")
        provider.pull_domain_events()
        provider.resume()  # Already active
        events = provider.pull_domain_events()
        assert len(events) == 0

    def test_router_settings_defaults(self):
        settings = LLMRouterSettings(group_name="karsa-reasoning")
        assert settings.routing_strategy == RoutingStrategy.LATENCY.value
        assert settings.num_retries == 3
        assert settings.timeout_seconds == 60
        assert settings.allowed_fails == 2

    def test_model_group_entry(self):
        entry = LLMModelGroupEntry(
            model_name="gpt-4o",
            provider_id="p1",
            priority=10,
            temperature=0.2,
            max_tokens=4096,
        )
        assert entry.model_name == "gpt-4o"
        assert entry.is_active is True
