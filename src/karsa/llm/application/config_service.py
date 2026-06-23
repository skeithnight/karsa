"""LLM Pool configuration service.

Manages LLM providers, model groups, and router settings.
Uses CredentialEncryptionService from providers/ for API key encryption.
"""
import uuid
import logging
from typing import Dict, Any, Optional, List

from karsa.llm.domain.config_models import (
    LLMProvider,
    LLMProviderStatus,
    LLMCredential,
    LLMModelGroupEntry,
    LLMRouterSettings,
    RoutingStrategy,
)
from karsa.llm.infrastructure.storage.config_repository import LLMConfigRepository
from karsa.providers.application.credential_service import CredentialEncryptionService
from karsa.memory.infrastructure.event.postgres_event_bus import PostgresEventBus
from karsa.llm.events.events import (
    LLMModelGroupAddedEvent,
    LLMModelGroupRemovedEvent,
    LLMRouterSettingsUpdatedEvent,
)

logger = logging.getLogger(__name__)


class LLMConfigService:
    """Application service for LLM Pool configuration lifecycle."""

    def __init__(
        self,
        config_repo: LLMConfigRepository,
        credential_service: CredentialEncryptionService,
        event_bus: PostgresEventBus,
    ):
        self._repo = config_repo
        self._cred_service = credential_service
        self._event_bus = event_bus

    # --- Provider Management ---

    def register_provider(
        self,
        name: str,
        api_key: str,
        base_url: Optional[str] = None,
        priority: int = 100,
    ) -> LLMProvider:
        """Register an LLM provider with encrypted API key."""
        provider_id = str(uuid.uuid4())
        provider = LLMProvider(
            provider_id=provider_id,
            name=name,
            base_url=base_url,
            priority=priority,
        )

        encrypted = self._cred_service.encrypt(api_key)
        self._repo.add_provider(provider)
        self._repo.save_credential(provider_id, encrypted)
        self._publish_events(provider)

        logger.info(f"Registered LLM provider {name} (id={provider_id})")
        return provider

    def rotate_api_key(self, provider_id: str, new_api_key: str) -> None:
        """Rotate an LLM provider's API key."""
        existing = self._repo.get_credential(provider_id)
        new_version = (existing.key_rotation_version + 1) if existing else 1
        encrypted = self._cred_service.encrypt(new_api_key, key_rotation_version=new_version)
        self._repo.save_credential(provider_id, encrypted)
        logger.info(f"Rotated API key for LLM provider {provider_id} (v{new_version})")

    def get_decrypted_key(self, provider_id: str) -> Optional[str]:
        """Get decrypted API key for runtime use."""
        cred = self._repo.get_credential(provider_id)
        if not cred:
            return None
        return self._cred_service.decrypt(cred)

    def pause_provider(self, provider_id: str) -> None:
        provider = self._repo.get_provider(provider_id)
        if provider:
            provider.pause()
            self._repo.save_provider(provider)
            self._publish_events(provider)

    def resume_provider(self, provider_id: str) -> None:
        provider = self._repo.get_provider(provider_id)
        if provider:
            provider.resume()
            self._repo.save_provider(provider)
            self._publish_events(provider)

    def list_providers(self) -> List[LLMProvider]:
        return self._repo.list_providers()

    # --- Model Group Management ---

    def add_model_to_group(
        self,
        group_name: str,
        model_name: str,
        provider_name: str,
        priority: int = 100,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> None:
        """Add a model to a named group (e.g., 'karsa-reasoning')."""
        provider = self._repo.get_provider_by_name(provider_name)
        if not provider:
            raise ValueError(f"LLM provider '{provider_name}' not found")

        entry = LLMModelGroupEntry(
            model_name=model_name,
            provider_id=provider.provider_id,
            priority=priority,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self._repo.add_model_group(group_name, entry)
        self._event_bus.publish(LLMModelGroupAddedEvent(
            group_name=group_name,
            model_name=model_name,
            provider_id=provider.provider_id,
            priority=priority,
        ))
        logger.info(f"Added {model_name} ({provider_name}) to group '{group_name}'")

    def get_model_group(self, group_name: str) -> List[LLMModelGroupEntry]:
        """Get all active models in a group, ordered by priority."""
        return self._repo.get_model_group(group_name)

    def remove_model_from_group(self, group_name: str, model_name: str, provider_name: str) -> None:
        provider = self._repo.get_provider_by_name(provider_name)
        if provider:
            self._repo.remove_model_group_entry(group_name, model_name, provider.provider_id)

    # --- Router Settings ---

    def update_router_settings(
        self,
        group_name: str,
        routing_strategy: str = RoutingStrategy.LATENCY.value,
        num_retries: int = 3,
        timeout_seconds: int = 60,
        allowed_fails: int = 2,
    ) -> None:
        settings = LLMRouterSettings(
            group_name=group_name,
            routing_strategy=routing_strategy,
            num_retries=num_retries,
            timeout_seconds=timeout_seconds,
            allowed_fails=allowed_fails,
        )
        self._repo.save_router_settings(settings)
        self._event_bus.publish(LLMRouterSettingsUpdatedEvent(
            group_name=group_name,
            routing_strategy=routing_strategy,
            num_retries=num_retries,
            timeout_seconds=timeout_seconds,
        ))
        logger.info(f"Updated router settings for '{group_name}': {routing_strategy}")

    def get_router_settings(self, group_name: str) -> Optional[LLMRouterSettings]:
        return self._repo.get_router_settings(group_name)

    # --- System Config ---

    def set_system_config(self, domain: str, key: str, value: Any, description: str = "") -> None:
        self._repo.save_system_config(domain, key, value, description)

    def get_system_config(self, domain: str, key: str) -> Optional[Any]:
        return self._repo.get_system_config(domain, key)

    def get_all_system_configs(self, domain: str) -> Dict[str, Any]:
        return self._repo.get_all_system_configs(domain)

    # --- Internal ---

    def _publish_events(self, provider: LLMProvider) -> None:
        events = provider.pull_domain_events()
        for event in events:
            self._event_bus.publish(event)
