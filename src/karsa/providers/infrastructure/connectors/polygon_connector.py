"""Polygon.io WebSocket connector.

Sprint-52: Real-time tick data ingestion via Polygon WebSocket API.
Registered as 'polygon' in the ConnectorFactory.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, Awaitable

import websockets

from karsa.providers.application.connector_factory import BaseConnector, register_connector
from karsa.providers.domain.normalization import NormalizedMarketTick, EventType, DeadLetterEntry
from karsa.providers.infrastructure.storage.dead_letter_repository import DeadLetterRepository

logger = logging.getLogger(__name__)

# Massive (formerly Polygon.io) WebSocket endpoint
POLYGON_WS_URL = "wss://socket.massive.com/stocks"


@register_connector("polygon")
class PolygonConnector(BaseConnector):
    """Polygon.io WebSocket connector for real-time stock ticks.

    Connects to Polygon's WebSocket API, subscribes to trades
    for configured symbols, and emits NormalizedMarketTick events.
    """

    def __init__(self, provider_id: str, config: Dict[str, Any], credentials: Dict[str, str], dead_letter_repo: Optional[DeadLetterRepository] = None):
        super().__init__(provider_id, config, credentials)
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._task: Optional[asyncio.Task] = None
        self._drain_task: Optional[asyncio.Task] = None
        self._on_tick: Optional[Callable[[NormalizedMarketTick], Awaitable[None]]] = None
        self._dead_letter_repo = dead_letter_repo
        self._symbols = config.get("symbols", [])
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 30.0
        self._message_timeout = config.get("message_timeout_seconds", 60.0)
        # Backpressure queue — separates WebSocket receive from downstream processing
        self._queue: asyncio.Queue[Optional[NormalizedMarketTick]] = asyncio.Queue(
            maxsize=config.get("tick_queue_size", 50000)
        )

    def set_on_tick(self, callback: Callable[[NormalizedMarketTick], Awaitable[None]]) -> None:
        """Set the callback for incoming ticks."""
        self._on_tick = callback

    async def start(self) -> None:
        """Initialize WebSocket connection and subscribe to symbols."""
        self._running = True
        self._task = asyncio.create_task(self._connection_loop())
        self._drain_task = asyncio.create_task(self._drain_queue())
        logger.info(f"PolygonConnector started for {len(self._symbols)} symbols")

    async def stop(self) -> None:
        """Gracefully close the WebSocket connection."""
        self._running = False
        # Close WebSocket first (unblocks recv() in _receive_loop)
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        # Cancel connection loop task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        # Signal drain task to exit via sentinel, then cancel as fallback
        try:
            self._queue.put_nowait(None)
        except asyncio.QueueFull:
            pass
        if self._drain_task:
            self._drain_task.cancel()
            try:
                await self._drain_task
            except asyncio.CancelledError:
                pass
            self._drain_task = None
        logger.info("PolygonConnector stopped")

    async def reset(self) -> None:
        """Reset internal state for supervised restart.

        Cancels orphaned tasks, drains the queue, and creates a fresh queue
        so the next start() begins clean.
        """
        await self.stop()
        # Create a fresh queue — old drain task references are gone
        self._queue = asyncio.Queue(
            maxsize=self._queue.maxsize if hasattr(self._queue, 'maxsize') else 50000
        )
        self._ws = None
        logger.info("PolygonConnector reset for restart")

    async def health_check(self) -> bool:
        """Check if the WebSocket is connected."""
        if self._ws is None:
            return False
        try:
            return self._ws.open
        except AttributeError:
            # websockets >= 14 uses ws.connection.open
            try:
                return self._ws.connection is not None and self._ws.connection.open
            except Exception:
                return False

    async def _connection_loop(self) -> None:
        """Main connection loop with auto-reconnect and backoff."""
        delay = self._reconnect_delay
        consecutive_failures = 0
        max_consecutive_failures = 10  # Stop reconnecting after 10 rapid failures

        while self._running:
            try:
                async with websockets.connect(POLYGON_WS_URL) as ws:
                    self._ws = ws
                    await self._authenticate(ws)
                    await self._subscribe(ws)
                    consecutive_failures = 0  # Reset on successful connection
                    delay = self._reconnect_delay
                    await self._receive_loop(ws)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                consecutive_failures += 1
                self._ws = None

                if consecutive_failures >= max_consecutive_failures:
                    logger.error(
                        f"PolygonConnector: {consecutive_failures} consecutive failures. "
                        f"Last error: {e}. Backing off to {self._max_reconnect_delay}s intervals."
                    )
                    delay = self._max_reconnect_delay

                if self._running:
                    logger.error(f"PolygonConnector connection error ({consecutive_failures}): {e}")
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, self._max_reconnect_delay)

    async def _authenticate(self, ws: websockets.WebSocketClientProtocol) -> None:
        """Send authentication message to Polygon."""
        api_key = self.credentials.get("api_key", "")
        auth_msg = json.dumps({"action": "auth", "params": api_key})
        await ws.send(auth_msg)
        # Wait for auth response
        response = await ws.recv()
        data = json.loads(response)
        status = data[0].get("status", "") if data else ""
        if status not in ("auth_success", "connected"):
            raise RuntimeError(f"Polygon auth failed: {data}")

    async def _subscribe(self, ws: websockets.WebSocketClientProtocol) -> None:
        """Subscribe to trade feeds for configured symbols."""
        if not self._symbols:
            logger.warning("No symbols configured for Polygon subscription")
            return
        params = ",".join(f"T.{s}" for s in self._symbols)
        sub_msg = json.dumps({"action": "subscribe", "params": params})
        await ws.send(sub_msg)
        logger.info(f"Polygon subscribed to: {self._symbols}")

    async def _receive_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        """Process incoming messages with timeout and backpressure queue."""
        while self._running:
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=self._message_timeout)
            except asyncio.TimeoutError:
                logger.warning(f"No Polygon messages for {self._message_timeout}s — reconnecting")
                break
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Polygon receive error: {e}")
                break

            try:
                data = json.loads(message)
                for event in data:
                    if event.get("ev") == "T":  # Trade event
                        tick = self._normalize_trade(event)
                        if tick:
                            try:
                                self._queue.put_nowait(tick)
                            except asyncio.QueueFull:
                                # Drop oldest to make room — backpressure
                                try:
                                    self._queue.get_nowait()
                                except asyncio.QueueEmpty:
                                    pass
                                self._queue.put_nowait(tick)
                                logger.warning("Tick queue full — dropped oldest tick")
            except json.JSONDecodeError as e:
                logger.warning(f"Polygon JSON decode error: {e}")
            except Exception as e:
                logger.error(f"Polygon message processing error: {e}")

    async def _drain_queue(self) -> None:
        """Separate task drains queue → downstream callback (aggregation/emission)."""
        while self._running:
            try:
                tick = await self._queue.get()
                if tick is None:  # Shutdown signal
                    break
                if self._on_tick:
                    await self._on_tick(tick)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Queue drain error: {e}")

    def _normalize_trade(self, event: dict) -> Optional[NormalizedMarketTick]:
        """Normalize a Polygon trade event to NormalizedMarketTick."""
        try:
            return NormalizedMarketTick(
                symbol=event.get("sym", ""),
                price=float(event.get("p", 0)),
                volume=int(event.get("s", 0)),
                timestamp_utc=datetime.fromtimestamp(
                    event.get("t", 0) / 1000, tz=timezone.utc
                ),
                source_provider="polygon",
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"Polygon normalization error: {e} | raw: {event}")
            if self._dead_letter_repo:
                try:
                    self._dead_letter_repo.append(DeadLetterEntry(
                        provider_id=self.provider_id,
                        raw_payload=event,
                        error_message=str(e),
                        error_type="TYPE_COERCION",
                    ))
                except Exception as dl_err:
                    logger.error(f"Dead letter write failed: {dl_err}")
            return None
