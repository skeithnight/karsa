"""Config Manager — zero-downtime hot-reload via pg_notify.

Sprint-51: Listens for provider_config_updated notifications
and performs blue/green connector swaps without restarting.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime

import psycopg

from karsa.providers.domain.data_bridge import (
    DataBridgeProvider,
    ProviderStatus,
    EncryptedCredential,
    ProviderConfig,
    HealthStatus,
    HealthLogEntry,
)
from karsa.providers.infrastructure.storage.data_bridge_repositories import (
    DataBridgeProviderRepository,
    ProviderHealthLogRepository,
)
from karsa.providers.application.credential_service import CredentialEncryptionService
from karsa.providers.application.connector_factory import ConnectorFactory, BaseConnector

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages provider configuration with zero-downtime hot-reload.

    Subscribes to pg_notify('provider_config_updated') and performs
    blue/green connector swaps when configuration changes.
    """

    def __init__(
        self,
        dsn: str,
        provider_repo: DataBridgeProviderRepository,
        health_repo: ProviderHealthLogRepository,
        credential_service: CredentialEncryptionService,
        on_tick: Optional[Callable] = None,
        on_news: Optional[Callable] = None,
        dead_letter_repo=None,
        health_monitor=None,
    ):
        self._dsn = dsn
        self._provider_repo = provider_repo
        self._health_repo = health_repo
        self._credential_service = credential_service
        self._on_tick = on_tick
        self._on_news = on_news
        self._dead_letter_repo = dead_letter_repo
        self._health_monitor = health_monitor
        # Active connectors: provider_id -> BaseConnector
        self._active_connectors: Dict[str, BaseConnector] = {}
        self._listener_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the pg_notify listener and initialize active connectors."""
        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        logger.info("ConfigManager started — listening for provider_config_updated")

    async def stop(self) -> None:
        """Stop the listener and gracefully shut down all connectors. Idempotent."""
        if not self._running:
            return
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        for provider_id, connector in self._active_connectors.items():
            try:
                await connector.stop()
                logger.info(f"Stopped connector for {provider_id}")
            except Exception as e:
                logger.error(f"Error stopping connector {provider_id}: {e}")
        self._active_connectors.clear()

    async def _listen_loop(self) -> None:
        """Background loop that listens for pg_notify events with reconnection."""
        while self._running:
            try:
                async with await psycopg.AsyncConnection.connect(self._dsn, autocommit=True) as conn:
                    await conn.execute("LISTEN provider_config_updated")
                    logger.info("LISTEN provider_config_updated established")
                    async for notify in conn.notifies():
                        if not self._running:
                            break
                        provider_id = notify.payload
                        logger.info(f"Received config change notification for {provider_id}")
                        await self._handle_config_change(provider_id)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"ConfigManager connection lost: {e}")
                if self._running:
                    logger.info("ConfigManager reconnecting in 5s...")
                    await asyncio.sleep(5)

    async def _handle_config_change(self, provider_id: str) -> None:
        """Handle a config change notification — blue/green swap."""
        try:
            # 1. Get provider from DB (async-wrapped)
            provider = await asyncio.to_thread(self._provider_repo.get, provider_id)
            if not provider:
                logger.warning(f"Config change for unknown provider {provider_id}")
                return

            # 2. Get new config and credentials (async-wrapped)
            configs = await asyncio.to_thread(self._provider_repo.get_all_configs, provider_id)
            cred = await asyncio.to_thread(self._provider_repo.get_credential, provider_id)
            if not cred:
                logger.error(f"No credentials found for {provider_id}")
                await self._log_health(provider_id, HealthStatus.AUTH_ERROR, "No credentials found")
                return

            # 3. Decrypt credentials
            try:
                decrypted_key = self._credential_service.decrypt(cred)
                credentials = {"api_key": decrypted_key}
            except Exception as e:
                logger.error(f"Credential decryption failed for {provider_id}: {e}")
                await self._log_health(provider_id, HealthStatus.AUTH_ERROR, str(e))
                return

            # 4. Create Blue connector
            try:
                blue = ConnectorFactory.create(
                    provider_name=provider.name,
                    provider_id=provider_id,
                    config=configs,
                    credentials=credentials,
                    dead_letter_repo=self._dead_letter_repo,
                )
                # Wire callbacks on Blue BEFORE swap (prevents silent data loss)
                if self._on_tick and hasattr(blue, 'set_on_tick'):
                    blue.set_on_tick(self._on_tick)
                if self._on_news and hasattr(blue, 'set_on_news'):
                    blue.set_on_news(self._on_news)

                # Validate Blue
                if not await blue.health_check():
                    raise RuntimeError("Blue connector health check failed")
            except Exception as e:
                logger.error(f"Blue connector creation failed for {provider_id}: {e}")
                await self._log_health(provider_id, HealthStatus.DISCONNECTED, str(e))
                return

            # 5. Atomic swap: save old ref, register Blue, then drain Green
            green = self._active_connectors.get(provider_id)
            self._active_connectors[provider_id] = blue
            if self._health_monitor:
                self._health_monitor.register_connector(provider_id, blue)

            # Drain the old (Green) connector after Blue is live
            if green:
                try:
                    await green.stop()
                    logger.info(f"Green connector drained for {provider_id}")
                except Exception as e:
                    logger.warning(f"Error draining Green connector: {e}")

            logger.info(f"Blue/green swap completed for {provider_id}")
            await self._log_health(provider_id, HealthStatus.CONNECTED)

        except Exception as e:
            logger.error(f"Config change handler error for {provider_id}: {e}")

    def get_connector(self, provider_id: str) -> Optional[BaseConnector]:
        """Get the active connector for a provider."""
        return self._active_connectors.get(provider_id)

    async def _log_health(
        self,
        provider_id: str,
        status: HealthStatus,
        error_message: Optional[str] = None,
        latency_ms: Optional[int] = None,
    ) -> None:
        """Append a health log entry (async-wrapped to avoid blocking)."""
        entry = HealthLogEntry(
            provider_id=provider_id,
            status=status,
            error_message=error_message,
            latency_ms=latency_ms,
        )
        try:
            await asyncio.to_thread(self._health_repo.append, entry)
        except Exception as e:
            logger.error(f"Failed to log health for {provider_id}: {e}")
