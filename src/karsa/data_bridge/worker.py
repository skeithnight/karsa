"""Data Bridge Worker — entry point for the data ingestion pipeline.

Boots all Data Bridge services in an async event loop:
- ConfigManager (pg_notify hot-reload)
- HealthMonitorService (background health checks)
- Connectors (Polygon WebSocket, Finnhub REST)
- AggregationEngine (tick → OHLCV bars)
- EventEmitter (publishes to Karsa event bus)

Usage:
    uv run python -m karsa.data_bridge.worker
    uv run python src/karsa/data_bridge/worker.py
"""
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from typing import Dict

from psycopg_pool import ConnectionPool
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from karsa.memory.infrastructure.event.postgres_event_bus import PostgresEventBus
from karsa.providers.application.credential_service import CredentialEncryptionService
from karsa.providers.application.config_manager import ConfigManager
from karsa.providers.application.health_monitor import HealthMonitorService
from karsa.providers.application.failover_service import FailoverService
from karsa.providers.application.gap_fill_service import GapFillService
from karsa.providers.application.aggregation_engine import AggregationEngine
from karsa.providers.application.event_emitter import DataBridgeEventEmitter
from karsa.providers.application.connector_factory import ConnectorFactory, BaseConnector
from karsa.providers.infrastructure.storage.data_bridge_repositories import (
    DataBridgeProviderRepository,
    ProviderHealthLogRepository,
)
from karsa.providers.infrastructure.storage.dead_letter_repository import DeadLetterRepository
from karsa.providers.domain.data_bridge import HealthStatus
from karsa.providers.domain.normalization import NormalizedAggregatedBar, NormalizedNewsEvent
from karsa.data_bridge.durable_buffer import DurableBarBuffer
from karsa.data_bridge.health_server import HealthServer

# Import connectors to register them
import karsa.providers.infrastructure.connectors  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("data_bridge.worker")


class DataBridgeWorker:
    """Main orchestrator for the Data Bridge ingestion pipeline.

    Wires together all services and manages the async lifecycle.
    """

    def __init__(self):
        self._pool: ConnectionPool = None
        self._sa_engine = None
        self._event_bus: PostgresEventBus = None
        self._config_manager: ConfigManager = None
        self._health_monitor: HealthMonitorService = None
        self._failover_service: FailoverService = None
        self._aggregation_engine: AggregationEngine = None
        self._event_emitter: DataBridgeEventEmitter = None
        self._running = False
        self._stopped = False  # Idempotency guard for stop()
        self._connector_tasks: list = []  # Supervised connector tasks
        self._durable_buffer: DurableBarBuffer = None
        self._health_server: HealthServer = None
        self._repos: list = []  # Track repos for session refresh
        self._session_refresh_counter = 0
        self._SESSION_REFRESH_INTERVAL = 3600  # Refresh session every ~1 hour (in loop ticks)

    async def start(self) -> None:
        """Boot all services and start the ingestion pipeline."""
        logger.info("=" * 60)
        logger.info("KARSA DATA BRIDGE WORKER — STARTING")
        logger.info("=" * 60)

        # 1. Database connection
        self._pool = self._create_pool()

        # SQLAlchemy engine + session factory for repositories (they use ORM queries)
        db_url = self._build_sqlalchemy_url()
        self._sa_engine = create_engine(db_url, pool_size=5, max_overflow=10)
        self._SessionFactory = sessionmaker(bind=self._sa_engine)
        sa_session = self._SessionFactory()

        # 2. Event bus
        self._event_bus = PostgresEventBus(self._pool)

        # 3. Repositories (require SQLAlchemy Session)
        provider_repo = DataBridgeProviderRepository(sa_session)
        health_repo = ProviderHealthLogRepository(sa_session)
        dead_letter_repo = DeadLetterRepository(sa_session)
        # Track repos for periodic session refresh
        self._repos = [provider_repo, health_repo, dead_letter_repo]

        # 4. Durable buffer (SQLite WAL — crash-safe bar persistence)
        self._durable_buffer = DurableBarBuffer()
        self._durable_buffer.open()

        # 5. Credential service
        try:
            credential_service = CredentialEncryptionService()
        except Exception as e:
            logger.critical(f"Cannot start without DATA_BRIDGE_MASTER_KEY: {e}")
            sys.exit(1)

        # 5. Event emitter (connects aggregation → event bus)
        self._event_emitter = DataBridgeEventEmitter(self._event_bus)

        # 6. Bar queue — backpressure between aggregation and emission
        self._bar_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._bar_drain_task = None

        # 7. Aggregation engine (tick → bar → bar queue)
        self._aggregation_engine = AggregationEngine(
            timeframes=["1m", "5m"],
            on_bar=self._enqueue_bar,
        )

        # 7. Failover service
        dsn = self._build_dsn()
        self._failover_service = FailoverService(
            provider_repo=provider_repo,
            health_repo=health_repo,
            credential_service=credential_service,
            event_bus=self._event_bus,
        )

        # 8. Shared connector registry — both HealthMonitor and ConfigManager
        # reference the same dict to prevent registry drift
        shared_connectors: Dict[str, BaseConnector] = {}

        # 9. Config manager (pg_notify hot-reload)
        self._config_manager = ConfigManager(
            dsn=dsn,
            provider_repo=provider_repo,
            health_repo=health_repo,
            credential_service=credential_service,
            on_tick=self._on_tick,
            on_news=self._on_news,
            dead_letter_repo=dead_letter_repo,
        )
        # Override ConfigManager's internal dict with shared one
        self._config_manager._active_connectors = shared_connectors

        # 10. Health monitor — uses shared connector registry
        self._health_monitor = HealthMonitorService(
            health_repo=health_repo,
            provider_repo=provider_repo,
            check_interval_seconds=30,
            on_degraded=self._on_provider_degraded,
            shared_connectors=shared_connectors,
        )
        # Wire health_monitor reference back into ConfigManager for re-registration on swap
        self._config_manager._health_monitor = self._health_monitor

        # 10. Boot services
        self._running = True
        await self._config_manager.start()
        await self._health_monitor.start()

        # 10b. Start health check HTTP server (for K8s liveness/readiness probes)
        health_port = int(os.environ.get("HEALTH_PORT", "8080"))
        self._health_server = HealthServer(
            port=health_port,
            get_connectors=lambda: dict(self._config_manager._active_connectors),
            get_queue_depth=lambda: self._bar_queue.qsize() if self._bar_queue else 0,
            get_buffer_stats=lambda: {
                "pending_bars": self._durable_buffer.pending_bar_count if self._durable_buffer else 0,
                "pending_news": self._durable_buffer.pending_news_count if self._durable_buffer else 0,
            },
        )
        await self._health_server.start()

        # 11. Start bar drain task (reads from bar_queue → event emitter)
        self._bar_drain_task = asyncio.create_task(self._bar_drain_loop())

        # 12. Replay unflushed bars/news from durable buffer (after drain task exists)
        pending_bars = self._durable_buffer.pending_bar_count
        pending_news = self._durable_buffer.pending_news_count
        if pending_bars > 0 or pending_news > 0:
            logger.info(f"Replaying {pending_bars} bars and {pending_news} news from durable buffer")
            await self._replay_durable_buffer()

        # 13. Initialize active connectors from DB
        await self._initialize_connectors(provider_repo, credential_service, dead_letter_repo)

        logger.info("=" * 60)
        logger.info("KARSA DATA BRIDGE WORKER — RUNNING")
        logger.info(f"  Connectors: {list(self._config_manager._active_connectors.keys())}")
        logger.info(f"  Timeframes: {self._aggregation_engine._timeframes}")
        logger.info(f"  Health interval: 30s")
        logger.info("=" * 60)

        # 14. Run until shutdown
        try:
            while self._running:
                await asyncio.sleep(1)
                # Periodically evict stale aggregation buffers
                evicted = self._aggregation_engine.evict_stale_buffers()
                if evicted > 0:
                    logger.info(f"Evicted {evicted} stale buffers")
                # Periodically refresh SQLAlchemy sessions to prevent stale state
                self._session_refresh_counter += 1
                if self._session_refresh_counter >= self._SESSION_REFRESH_INTERVAL:
                    self._refresh_sessions()
                    self._session_refresh_counter = 0
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        """Gracefully shut down all services. Idempotent — safe to call multiple times."""
        if self._stopped:
            return
        self._stopped = True
        self._running = False

        logger.info("Shutting down Data Bridge Worker...")

        # Stop health server first (so K8s stops routing traffic)
        if self._health_server:
            await self._health_server.stop()

        # Cancel bar drain task
        if self._bar_drain_task and not self._bar_drain_task.done():
            self._bar_drain_task.cancel()
            try:
                await self._bar_drain_task
            except asyncio.CancelledError:
                pass

        # Cancel supervised connector tasks
        for task in self._connector_tasks:
            if not task.done():
                task.cancel()
        if self._connector_tasks:
            await asyncio.gather(*self._connector_tasks, return_exceptions=True)
            self._connector_tasks.clear()

        # Flush remaining aggregation buffers
        if self._aggregation_engine:
            await self._aggregation_engine.flush_all()

        # Stop services in reverse order
        if self._health_monitor:
            await self._health_monitor.stop()
        if self._config_manager:
            await self._config_manager.stop()

        # Close durable buffer
        if self._durable_buffer:
            self._durable_buffer.close()

        # Close SQLAlchemy engine
        if self._sa_engine:
            self._sa_engine.dispose()

        # Close DB pool
        if self._pool:
            self._pool.close()

        logger.info("Data Bridge Worker stopped.")

    async def _initialize_connectors(
        self,
        provider_repo: DataBridgeProviderRepository,
        credential_service: CredentialEncryptionService,
        dead_letter_repo: DeadLetterRepository,
    ) -> None:
        """Load active providers from DB and create connectors with supervised tasks."""
        active_providers = await asyncio.to_thread(provider_repo.list_active)
        for provider in active_providers:
            try:
                # Get config and credentials (async-wrapped to avoid blocking)
                configs = await asyncio.to_thread(provider_repo.get_all_configs, provider.provider_id)
                cred = await asyncio.to_thread(provider_repo.get_credential, provider.provider_id)
                if cred:
                    decrypted_key = credential_service.decrypt(cred)
                    credentials = {"api_key": decrypted_key}
                else:
                    # Some connectors (idx_api, saham_mcp, yfinance) don't need API keys
                    credentials = {}
                    logger.info(f"No credentials for {provider.name}, using empty credentials")

                # Create connector
                connector = ConnectorFactory.create(
                    provider_name=provider.name,
                    provider_id=provider.provider_id,
                    config=configs,
                    credentials=credentials,
                    dead_letter_repo=dead_letter_repo,
                )

                # Wire callbacks based on connector type
                if hasattr(connector, "set_on_tick"):
                    connector.set_on_tick(self._on_tick)
                if hasattr(connector, "set_on_news"):
                    connector.set_on_news(self._on_news)
                if hasattr(connector, "set_on_bar"):
                    connector.set_on_bar(self._enqueue_bar)  # Direct to bar queue, skips aggregation

                # Register with health monitor and config manager BEFORE starting
                self._health_monitor.register_connector(provider.provider_id, connector)
                self._config_manager._active_connectors[provider.provider_id] = connector

                # Start connector under supervision
                task = asyncio.create_task(
                    self._supervised_connector(provider, connector),
                    name=f"connector:{provider.name}:{provider.provider_id}",
                )
                self._connector_tasks.append(task)

                logger.info(f"Initialized connector: {provider.name} (id={provider.provider_id})")

            except Exception as e:
                logger.error(f"Failed to initialize connector {provider.name}: {e}")

    async def _supervised_connector(self, provider, connector) -> None:
        """Run a connector with automatic restart on crash.

        If the connector's internal task raises an unhandled exception,
        log it, wait, and restart. Only exits when self._running is False
        or the task is cancelled.
        """
        while self._running:
            try:
                await connector.start()
                # Block until connector's internal task completes or crashes
                if hasattr(connector, '_task') and connector._task:
                    await connector._task
                elif hasattr(connector, '_drain_task') and connector._drain_task:
                    await connector._drain_task
                else:
                    # No internal task — connector finished synchronously
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Connector {provider.name} (id={provider.provider_id}) crashed: {e}. "
                    f"Restarting in 5s..."
                )
                try:
                    await asyncio.sleep(5)
                except asyncio.CancelledError:
                    break
                # Reset connector state (cancels orphaned tasks, clears queues)
                try:
                    await connector.reset()
                except Exception as reset_err:
                    logger.warning(f"Connector reset failed: {reset_err}")
                connector._running = True

    async def _on_tick(self, tick) -> None:
        """Callback for incoming ticks from connectors."""
        await self._aggregation_engine.process_tick(tick)

    async def _enqueue_bar(self, bar: NormalizedAggregatedBar) -> None:
        """Enqueue bar for emission — writes to durable buffer first, then in-memory queue."""
        # Write to durable buffer (crash-safe persistence)
        try:
            await asyncio.to_thread(self._durable_buffer.write_bar, bar)
        except Exception as e:
            logger.error(f"Durable buffer write failed: {e}")

        # Then enqueue in memory for fast processing
        try:
            self._bar_queue.put_nowait(bar)
        except asyncio.QueueFull:
            # Drop oldest bar to make room (prefer recent data)
            try:
                self._bar_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._bar_queue.put_nowait(bar)
            logger.warning("Bar queue full — dropped oldest bar")

    async def _bar_drain_loop(self) -> None:
        """Drain bar queue → event emitter. Runs until shutdown."""
        flushed_count = 0
        while self._running:
            try:
                bar = await asyncio.wait_for(self._bar_queue.get(), timeout=1.0)
                await self._event_emitter.emit_bar(bar)
                flushed_count += 1

                # Batch-mark flushed bars in durable buffer (every 100)
                if flushed_count >= 100:
                    await asyncio.to_thread(
                        self._durable_buffer.mark_bars_flushed, flushed_count
                    )
                    flushed_count = 0
            except asyncio.TimeoutError:
                # Periodically flush the mark counter even on idle
                if flushed_count > 0:
                    await asyncio.to_thread(
                        self._durable_buffer.mark_bars_flushed, flushed_count
                    )
                    flushed_count = 0
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Bar drain error: {e}")

        # Flush remaining bars on shutdown
        while not self._bar_queue.empty():
            try:
                bar = self._bar_queue.get_nowait()
                await self._event_emitter.emit_bar(bar)
                flushed_count += 1
            except asyncio.QueueEmpty:
                break

        # Final mark-flush
        if flushed_count > 0:
            await asyncio.to_thread(
                self._durable_buffer.mark_bars_flushed, flushed_count
            )

    async def _replay_durable_buffer(self) -> None:
        """Replay unflushed bars and news from durable buffer after crash."""
        try:
            # Replay bars
            bars = await asyncio.to_thread(self._durable_buffer.replay_unflushed_bars)
            for bar in bars:
                await self._event_emitter.emit_bar(bar)
            if bars:
                await asyncio.to_thread(
                    self._durable_buffer.mark_bars_flushed, len(bars)
                )
                logger.info(f"Replayed {len(bars)} bars from durable buffer")

            # Replay news
            news_list = await asyncio.to_thread(self._durable_buffer.replay_unflushed_news)
            for news in news_list:
                await self._event_emitter.emit_news(news)
            if news_list:
                await asyncio.to_thread(
                    self._durable_buffer.mark_news_flushed, len(news_list)
                )
                logger.info(f"Replayed {len(news_list)} news from durable buffer")

            # Cleanup old flushed rows
            await asyncio.to_thread(self._durable_buffer.cleanup_flushed, 24)
        except Exception as e:
            logger.error(f"Durable buffer replay failed: {e}")

    async def _on_news(self, news: NormalizedNewsEvent) -> None:
        """Callback for incoming news from connectors."""
        # Write to durable buffer (crash-safe persistence)
        try:
            await asyncio.to_thread(self._durable_buffer.write_news, news)
        except Exception as e:
            logger.error(f"Durable buffer news write failed: {e}")
        await self._event_emitter.emit_news(news)

    async def _on_provider_degraded(
        self,
        provider_id: str,
        status: HealthStatus,
        error_message: str,
    ) -> None:
        """Callback when health monitor detects degradation."""
        logger.warning(f"Provider {provider_id} degraded: {status.value} — triggering failover")
        active_connectors = self._config_manager._active_connectors
        await self._failover_service.handle_degradation(
            provider_id, status, error_message, active_connectors,
        )

    def _refresh_sessions(self) -> None:
        """Recreate SQLAlchemy session and inject into all repos.

        Prevents stale identity-map accumulation and recovers from
        transient connection errors in long-running sessions.
        """
        try:
            new_session = self._SessionFactory()
            for repo in self._repos:
                repo.session = new_session
            logger.info("SQLAlchemy session refreshed")
        except Exception as e:
            logger.error(f"Session refresh failed: {e}")

    def _create_pool(self) -> ConnectionPool:
        """Create PostgreSQL connection pool."""
        dsn = self._build_dsn()
        logger.info(f"Connecting to PostgreSQL: {self._mask_dsn(dsn)}")
        return ConnectionPool(dsn, min_size=2, max_size=10)

    def _build_dsn(self) -> str:
        """Build PostgreSQL DSN from environment variables."""
        db_name = os.environ.get("POSTGRES_DB", "karsa_db")
        db_user = os.environ.get("POSTGRES_USER", "karsa")
        db_pass = os.environ.get("POSTGRES_PASSWORD", "karsa_password")
        db_host = os.environ.get("POSTGRES_HOST", "localhost")
        db_port = os.environ.get("POSTGRES_PORT", "5432")
        return f"dbname={db_name} user={db_user} password={db_pass} host={db_host} port={db_port}"

    def _build_sqlalchemy_url(self) -> str:
        """Build SQLAlchemy connection URL."""
        db_name = os.environ.get("POSTGRES_DB", "karsa_db")
        db_user = os.environ.get("POSTGRES_USER", "karsa")
        db_pass = os.environ.get("POSTGRES_PASSWORD", "karsa_password")
        db_host = os.environ.get("POSTGRES_HOST", "localhost")
        db_port = os.environ.get("POSTGRES_PORT", "5432")
        return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    def _mask_dsn(self, dsn: str) -> str:
        """Mask password in DSN for logging."""
        import re
        return re.sub(r"password=\S+", "password=***", dsn)


async def main():
    """Main entry point."""
    worker = DataBridgeWorker()
    shutdown_event = asyncio.Event()

    def _signal_handler() -> None:
        """Set shutdown event — safe to call from signal context."""
        if not shutdown_event.is_set():
            logger.info("Shutdown signal received")
            shutdown_event.set()

    # Register signal handlers on the running loop
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    try:
        # Start worker in a separate task so we can await shutdown_event
        worker_task = asyncio.create_task(worker.start())
        # Wait for either worker completion or shutdown signal
        done, pending = await asyncio.wait(
            [worker_task, asyncio.create_task(shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED,
        )
        # Cancel any remaining pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    except KeyboardInterrupt:
        pass
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
