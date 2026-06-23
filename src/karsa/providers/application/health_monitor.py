"""Health Monitor — background task for connector health tracking.

Sprint-53: Periodically pings active connectors, logs latency,
detects degraded states, and triggers automatic failover.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Callable, Awaitable

from karsa.providers.domain.data_bridge import (
    HealthStatus,
    HealthLogEntry,
)
from karsa.providers.infrastructure.storage.data_bridge_repositories import (
    DataBridgeProviderRepository,
    ProviderHealthLogRepository,
)
from karsa.providers.application.connector_factory import BaseConnector

logger = logging.getLogger(__name__)


class HealthMonitorService:
    """Background service that monitors connector health.

    Pings all active connectors at a configurable interval,
    logs latency to provider_health_logs, and triggers
    failover when degraded states are detected.
    """

    def __init__(
        self,
        health_repo: ProviderHealthLogRepository,
        provider_repo: DataBridgeProviderRepository,
        check_interval_seconds: int = 30,
        on_degraded: Optional[Callable[[str, HealthStatus, str], Awaitable[None]]] = None,
        shared_connectors: Optional[Dict[str, BaseConnector]] = None,
    ):
        self._health_repo = health_repo
        self._provider_repo = provider_repo
        self._check_interval = check_interval_seconds
        self._on_degraded = on_degraded
        self._task: Optional[asyncio.Task] = None
        self._running = False
        # provider_id -> last known status
        self._status_cache: Dict[str, HealthStatus] = {}
        # Shared connector registry — if provided, uses the same dict as ConfigManager
        # to prevent registry drift. If None, uses internal dict.
        self._connectors: Dict[str, BaseConnector] = shared_connectors if shared_connectors is not None else {}

    def register_connector(self, provider_id: str, connector: BaseConnector) -> None:
        """Register a connector for health monitoring."""
        self._connectors[provider_id] = connector

    def unregister_connector(self, provider_id: str) -> None:
        """Remove a connector from monitoring."""
        self._connectors.pop(provider_id, None)
        self._status_cache.pop(provider_id, None)

    async def start(self) -> None:
        """Start the background health check loop."""
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"HealthMonitor started (interval={self._check_interval}s)")

    async def stop(self) -> None:
        """Stop the health check loop. Idempotent."""
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("HealthMonitor stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop — runs until stopped."""
        while self._running:
            try:
                await self._check_all_connectors()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"HealthMonitor check error: {e}")
            await asyncio.sleep(self._check_interval)

    async def _check_all_connectors(self) -> None:
        """Ping all registered connectors and log results."""
        for provider_id, connector in list(self._connectors.items()):
            try:
                start_time = time.monotonic()
                is_healthy = await connector.health_check()
                latency_ms = int((time.monotonic() - start_time) * 1000)

                if is_healthy:
                    new_status = HealthStatus.CONNECTED
                else:
                    new_status = HealthStatus.DISCONNECTED

                await self._record_health(provider_id, new_status, latency_ms)

            except Exception as e:
                logger.error(f"Health check failed for {provider_id}: {e}")
                await self._record_health(
                    provider_id,
                    HealthStatus.DISCONNECTED,
                    error_message=str(e),
                )

    async def _record_health(
        self,
        provider_id: str,
        new_status: HealthStatus,
        latency_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Record health status and trigger failover on state change."""
        old_status = self._status_cache.get(provider_id)
        self._status_cache[provider_id] = new_status

        # Always log to DB (wrap sync call to avoid blocking event loop)
        entry = HealthLogEntry(
            provider_id=provider_id,
            status=new_status,
            latency_ms=latency_ms,
            error_message=error_message,
        )
        try:
            await asyncio.to_thread(self._health_repo.append, entry)
        except Exception as e:
            logger.error(f"Failed to write health log for {provider_id}: {e}")

        # Trigger failover on degradation (status changed to bad state)
        if old_status != new_status and new_status in (
            HealthStatus.AUTH_ERROR,
            HealthStatus.RATE_LIMITED,
            HealthStatus.DISCONNECTED,
        ):
            logger.warning(
                f"Provider {provider_id} degraded: {old_status} -> {new_status}"
            )
            if self._on_degraded:
                await self._on_degraded(provider_id, new_status, error_message or "")

    def get_status(self, provider_id: str) -> HealthStatus:
        """Get the last known health status for a provider."""
        return self._status_cache.get(provider_id, HealthStatus.DISCONNECTED)

    def get_all_statuses(self) -> Dict[str, HealthStatus]:
        """Get all known health statuses."""
        return dict(self._status_cache)

    @property
    def is_running(self) -> bool:
        return self._running
