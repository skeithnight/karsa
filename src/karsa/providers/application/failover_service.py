"""Failover Service — automatic provider swap on degradation.

Sprint-53: Queries fallback providers, performs blue/green
connector swap, and emits failover events.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from karsa.providers.domain.data_bridge import (
    HealthStatus,
    ProviderStatus,
)
from karsa.providers.infrastructure.storage.data_bridge_repositories import (
    DataBridgeProviderRepository,
    ProviderHealthLogRepository,
)
from karsa.providers.application.connector_factory import ConnectorFactory, BaseConnector
from karsa.providers.application.credential_service import CredentialEncryptionService
from karsa.providers.events.events import ProviderFailoverEvent
from karsa.providers.ports import AlertPort
from karsa.memory.infrastructure.event.postgres_event_bus import PostgresEventBus

logger = logging.getLogger(__name__)


class FailoverService:
    """Handles automatic failover when a provider degrades.

    On degradation:
    1. Queries data_providers for fallback of same type with higher priority
    2. Creates new connector via ConnectorFactory
    3. Validates fallback connector health
    4. Swaps active connector
    5. Emits ProviderFailoverEvent and sends alert
    """

    def __init__(
        self,
        provider_repo: DataBridgeProviderRepository,
        health_repo: ProviderHealthLogRepository,
        credential_service: CredentialEncryptionService,
        event_bus: PostgresEventBus,
        alert_port: Optional[AlertPort] = None,
    ):
        self._repo = provider_repo
        self._health_repo = health_repo
        self._cred_service = credential_service
        self._event_bus = event_bus
        self._alert_port = alert_port

    async def handle_degradation(
        self,
        degraded_provider_id: str,
        status: HealthStatus,
        error_message: str,
        active_connectors: dict,
    ) -> Optional[BaseConnector]:
        """Handle a degraded provider — attempt failover.

        Args:
            degraded_provider_id: ID of the degraded provider.
            status: The degraded health status.
            error_message: Error details.
            active_connectors: Dict of provider_id -> BaseConnector (mutated on swap).

        Returns:
            The new fallback connector, or None if no fallback available.
        """
        # 1. Get degraded provider info
        degraded = await asyncio.to_thread(self._repo.get, degraded_provider_id)
        if not degraded:
            logger.error(f"Degraded provider {degraded_provider_id} not found in DB")
            return None

        logger.info(
            f"Initiating failover for {degraded.name} "
            f"(type={degraded.type.value}, status={status.value})"
        )

        # 2. Find fallback provider of same type with higher priority (lower number)
        fallbacks = await asyncio.to_thread(self._repo.list_by_type, degraded.type.value)
        fallback = None
        for f in fallbacks:
            if f.provider_id != degraded_provider_id and f.status == ProviderStatus.ACTIVE:
                fallback = f
                break

        if not fallback:
            logger.error(f"No fallback provider found for type={degraded.type.value}")
            await self._alert(
                "No Fallback Available",
                f"Provider {degraded.name} degraded ({status.value}) and no fallback exists.",
                "critical",
            )
            return None

        # 3. Create fallback connector
        try:
            configs = await asyncio.to_thread(self._repo.get_all_configs, fallback.provider_id)
            cred = await asyncio.to_thread(self._repo.get_credential, fallback.provider_id)
            if not cred:
                raise RuntimeError(f"No credentials for fallback {fallback.name}")

            decrypted_key = self._cred_service.decrypt(cred)
            fallback_connector = ConnectorFactory.create(
                provider_name=fallback.name,
                provider_id=fallback.provider_id,
                config=configs,
                credentials={"api_key": decrypted_key},
            )

            # Validate fallback
            if not await fallback_connector.health_check():
                raise RuntimeError(f"Fallback {fallback.name} health check failed")

        except Exception as e:
            logger.error(f"Fallback connector creation failed: {e}")
            await self._alert(
                "Failover Failed",
                f"Fallback {fallback.name} failed to start: {e}",
                "critical",
            )
            return None

        # 4. Swap connectors
        old_connector = active_connectors.get(degraded_provider_id)
        if old_connector:
            try:
                await old_connector.stop()
            except Exception as e:
                logger.warning(f"Error stopping degraded connector: {e}")

        active_connectors[fallback.provider_id] = fallback_connector
        logger.info(f"Failover complete: {degraded.name} -> {fallback.name}")

        # 5. Emit event
        event = ProviderFailoverEvent(
            source_provider_id=degraded_provider_id,
            target_provider_id=fallback.provider_id,
            reason=f"{status.value}: {error_message}",
            source_provider_name=degraded.name,
            target_provider_name=fallback.name,
        )
        await self._event_bus.async_publish(event)

        # 6. Alert
        await self._alert(
            "Provider Failover",
            f"Switched from {degraded.name} to {fallback.name}\n"
            f"Reason: {status.value} — {error_message}",
            "warning",
            metadata={
                "source": degraded.name,
                "target": fallback.name,
                "reason": status.value,
            },
        )

        return fallback_connector

    async def _alert(
        self,
        title: str,
        message: str,
        severity: str = "info",
        metadata: Optional[dict] = None,
    ) -> None:
        """Send alert if alert port is configured."""
        if self._alert_port:
            try:
                await self._alert_port.send_alert(title, message, severity, metadata)
            except Exception as e:
                logger.error(f"Alert delivery failed: {e}")
