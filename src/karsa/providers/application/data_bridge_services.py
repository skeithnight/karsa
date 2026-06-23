"""Data Bridge provider management service.

Sprint-51: Register, pause, resume providers. Manage encrypted
credentials and JSONB configurations. Emits domain events.
"""
import uuid
import logging
from typing import Dict, Any, Optional, List

from karsa.providers.domain.data_bridge import (
    DataBridgeProvider,
    ProviderType,
    ProviderStatus,
    EncryptedCredential,
    ProviderConfig,
    HealthLogEntry,
    HealthStatus,
)
from karsa.providers.infrastructure.storage.data_bridge_repositories import (
    DataBridgeProviderRepository,
    ProviderHealthLogRepository,
)
from karsa.providers.application.credential_service import CredentialEncryptionService
from karsa.memory.infrastructure.event.postgres_event_bus import PostgresEventBus

logger = logging.getLogger(__name__)


class DataBridgeProviderService:
    """Application service for Data Bridge provider lifecycle management.

    Coordinates between domain aggregates, repositories, encryption,
    and event publishing.
    """

    def __init__(
        self,
        provider_repo: DataBridgeProviderRepository,
        health_repo: ProviderHealthLogRepository,
        credential_service: CredentialEncryptionService,
        event_bus: PostgresEventBus,
    ):
        self._repo = provider_repo
        self._health_repo = health_repo
        self._cred_service = credential_service
        self._event_bus = event_bus

    def register_provider(
        self,
        name: str,
        ptype: str,
        api_key: str,
        api_secret: Optional[str] = None,
        priority: int = 100,
        initial_config: Optional[Dict[str, Any]] = None,
    ) -> DataBridgeProvider:
        """Register a new data provider with encrypted credentials.

        Args:
            name: Unique provider name (e.g., 'polygon', 'finnhub').
            ptype: Provider type (market_tick, market_bar, news, sentiment).
            api_key: Plaintext API key (will be encrypted at rest).
            api_secret: Optional plaintext API secret.
            priority: Lower = higher priority for failover.
            initial_config: Optional initial JSONB configuration.

        Returns:
            The created DataBridgeProvider aggregate.
        """
        provider_id = str(uuid.uuid4())
        provider_type = ProviderType(ptype)

        # Create aggregate (emits ProviderRegisteredEvent)
        provider = DataBridgeProvider(
            provider_id=provider_id,
            name=name,
            ptype=provider_type,
            priority=priority,
        )

        # Encrypt credentials
        encrypted_key = self._cred_service.encrypt(api_key)
        encrypted_secret = self._cred_service.encrypt(api_secret) if api_secret else None

        # Persist
        self._repo.add(provider)
        self._repo.save_credential(provider_id, encrypted_key, encrypted_secret)

        if initial_config:
            for key, value in initial_config.items():
                self._repo.save_config(provider_id, key, value)

        # Publish events
        self._publish_events(provider)

        logger.info(f"Registered provider {name} (id={provider_id}, type={ptype})")
        return provider

    def update_config(
        self,
        provider_id: str,
        config_key: str,
        config_value: Dict[str, Any],
    ) -> None:
        """Update a provider's configuration (triggers hot-reload)."""
        provider = self._repo.get(provider_id)
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")

        self._repo.save_config(provider_id, config_key, config_value)
        provider.notify_config_changed(config_key)
        self._publish_events(provider)

        logger.info(f"Updated config '{config_key}' for provider {provider_id}")

    def rotate_credentials(
        self,
        provider_id: str,
        new_api_key: str,
        new_api_secret: Optional[str] = None,
    ) -> None:
        """Rotate provider credentials (increments key_rotation_version)."""
        provider = self._repo.get(provider_id)
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")

        existing_cred = self._repo.get_credential(provider_id)
        new_version = (existing_cred.key_rotation_version + 1) if existing_cred else 1

        encrypted_key = self._cred_service.encrypt(new_api_key, key_rotation_version=new_version)
        encrypted_secret = (
            self._cred_service.encrypt(new_api_secret, key_rotation_version=new_version)
            if new_api_secret
            else None
        )

        self._repo.save_credential(provider_id, encrypted_key, encrypted_secret)
        provider.notify_config_changed("credentials")
        self._publish_events(provider)

        logger.info(f"Rotated credentials for provider {provider_id} (v{new_version})")

    def pause_provider(self, provider_id: str) -> None:
        """Pause a provider."""
        provider = self._repo.get(provider_id)
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")
        provider.pause()
        self._repo.save(provider)
        self._publish_events(provider)
        logger.info(f"Paused provider {provider_id}")

    def resume_provider(self, provider_id: str) -> None:
        """Resume a paused provider."""
        provider = self._repo.get(provider_id)
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")
        provider.resume()
        self._repo.save(provider)
        self._publish_events(provider)
        logger.info(f"Resumed provider {provider_id}")

    def set_maintenance(self, provider_id: str) -> None:
        """Set provider to maintenance mode."""
        provider = self._repo.get(provider_id)
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")
        provider.set_maintenance()
        self._repo.save(provider)
        self._publish_events(provider)

    def log_health(
        self,
        provider_id: str,
        status: str,
        latency_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Record a health log entry for a provider."""
        entry = HealthLogEntry(
            provider_id=provider_id,
            status=HealthStatus(status),
            latency_ms=latency_ms,
            error_message=error_message,
        )
        self._health_repo.append(entry)

    def get_provider(self, provider_id: str) -> Optional[DataBridgeProvider]:
        """Get a provider by ID."""
        return self._repo.get(provider_id)

    def get_provider_by_name(self, name: str) -> Optional[DataBridgeProvider]:
        """Get a provider by name."""
        return self._repo.get_by_name(name)

    def list_active_providers(self) -> List[DataBridgeProvider]:
        """List all active providers ordered by priority."""
        return self._repo.list_active()

    def list_by_type(self, ptype: str) -> List[DataBridgeProvider]:
        """List active providers of a specific type."""
        return self._repo.list_by_type(ptype)

    def get_decrypted_key(self, provider_id: str) -> Optional[str]:
        """Get decrypted API key for a provider (runtime only)."""
        cred = self._repo.get_credential(provider_id)
        if not cred:
            return None
        return self._cred_service.decrypt(cred)

    def _publish_events(self, provider: DataBridgeProvider) -> None:
        """Pull and publish all pending domain events."""
        events = provider.pull_domain_events()
        for event in events:
            self._event_bus.publish(event)
