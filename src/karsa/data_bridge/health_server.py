"""Health Check Server — lightweight HTTP server for Kubernetes probes.

Runs as a background asyncio task alongside the main worker loop.
Exposes:
  GET /health  — liveness probe (is the process alive?)
  GET /ready   — readiness probe (are connectors connected?)
  GET /metrics — basic metrics (tick count, bar count, queue depth)
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("data_bridge.health")

# Minimal HTTP server using asyncio — no FastAPI/starlette dependency required.
# For production, swap with a lightweight framework if needed.


class HealthServer:
    """Lightweight HTTP health check server for Kubernetes probes.

    Runs on a background asyncio task. No external dependencies.
    """

    def __init__(
        self,
        port: int = 8080,
        get_connectors: Optional[Callable[[], Dict[str, Any]]] = None,
        get_queue_depth: Optional[Callable[[], int]] = None,
        get_buffer_stats: Optional[Callable[[], Dict[str, int]]] = None,
    ):
        self._port = port
        self._server: Optional[asyncio.AbstractServer] = None
        self._task: Optional[asyncio.Task] = None
        self._started_at: Optional[datetime] = None
        self._get_connectors = get_connectors
        self._get_queue_depth = get_queue_depth
        self._get_buffer_stats = get_buffer_stats

    async def start(self) -> None:
        """Start the health check HTTP server."""
        self._started_at = datetime.now(timezone.utc)
        self._server = await asyncio.start_server(
            self._handle_connection,
            "0.0.0.0",
            self._port,
        )
        logger.info(f"Health server listening on port {self._port}")

    async def stop(self) -> None:
        """Stop the health check server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Health server stopped")

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle an incoming HTTP request (minimal HTTP/1.1 parser)."""
        try:
            # Read request line + headers (max 4KB)
            data = await asyncio.wait_for(reader.readline(), timeout=5.0)
            request_line = data.decode("utf-8", errors="replace").strip()
            if not request_line:
                writer.close()
                return

            # Read and discard headers
            while True:
                header_line = await asyncio.wait_for(reader.readline(), timeout=5.0)
                if header_line == b"\r\n" or header_line == b"\n" or not header_line:
                    break

            # Parse method and path
            parts = request_line.split()
            if len(parts) < 2:
                await self._send_response(writer, 400, {"error": "Bad request"})
                return

            method, path = parts[0], parts[1]

            # Route
            if path == "/health":
                await self._handle_health(writer)
            elif path == "/ready":
                await self._handle_ready(writer)
            elif path == "/metrics":
                await self._handle_metrics(writer)
            else:
                await self._send_response(writer, 404, {"error": "Not found"})

        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.debug(f"Health server request error: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _handle_health(self, writer: asyncio.StreamWriter) -> None:
        """Liveness probe — always 200 if the event loop is running."""
        uptime = None
        if self._started_at:
            uptime = int((datetime.now(timezone.utc) - self._started_at).total_seconds())
        await self._send_response(writer, 200, {
            "status": "alive",
            "uptime_seconds": uptime,
        })

    async def _handle_ready(self, writer: asyncio.StreamWriter) -> None:
        """Readiness probe — 200 only if connectors are healthy."""
        connectors = {}
        if self._get_connectors:
            connectors = self._get_connectors()

        all_connected = True
        details = {}
        for provider_id, connector in connectors.items():
            try:
                is_healthy = await connector.health_check()
                details[provider_id] = "connected" if is_healthy else "disconnected"
                if not is_healthy:
                    all_connected = False
            except Exception as e:
                details[provider_id] = f"error: {e}"
                all_connected = False

        if not connectors:
            # No connectors registered yet — still booting, not ready
            await self._send_response(writer, 503, {
                "status": "not_ready",
                "reason": "no connectors registered",
            })
            return

        status_code = 200 if all_connected else 503
        await self._send_response(writer, status_code, {
            "status": "ready" if all_connected else "degraded",
            "connectors": details,
        })

    async def _handle_metrics(self, writer: asyncio.StreamWriter) -> None:
        """Basic metrics endpoint (JSON — swap with Prometheus format if needed)."""
        queue_depth = 0
        if self._get_queue_depth:
            queue_depth = self._get_queue_depth()

        buffer_stats = {}
        if self._get_buffer_stats:
            buffer_stats = self._get_buffer_stats()

        await self._send_response(writer, 200, {
            "queue_depth": queue_depth,
            "durable_buffer": buffer_stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        body: dict,
    ) -> None:
        """Send a minimal HTTP/1.1 JSON response."""
        status_phrases = {
            200: "OK",
            400: "Bad Request",
            404: "Not Found",
            503: "Service Unavailable",
        }
        phrase = status_phrases.get(status_code, "OK")
        body_bytes = json.dumps(body, default=str).encode("utf-8")

        response = (
            f"HTTP/1.1 {status_code} {phrase}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body_bytes)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode("utf-8") + body_bytes

        writer.write(response)
        await writer.drain()
