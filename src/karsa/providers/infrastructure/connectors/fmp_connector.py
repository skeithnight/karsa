"""Financial Modeling Prep (FMP) Connector — Sprint-61.

REST polling connector for IDX EOD prices and fundamentals.
Free tier: 250 req/day. API key required.
IDX tickers use .JK suffix (e.g., BBCA.JK).
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

import httpx

from karsa.providers.application.connector_factory import BaseConnector, register_connector
from karsa.providers.domain.normalization import NormalizedAggregatedBar, EventType

logger = logging.getLogger(__name__)

FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"


@register_connector("fmp")
class FMPConnector(BaseConnector):
    """Financial Modeling Prep connector for EOD prices.

    REST polling — fetches latest quote for each ticker on a configurable interval.
    Uses set_on_bar callback to emit NormalizedAggregatedBar directly.
    """

    def __init__(self, provider_id: str, config: dict, credentials: dict):
        super().__init__(provider_id, config, credentials)
        self._api_key = credentials.get("api_key", "")
        self._tickers = config.get("tickers", [])
        self._poll_interval = config.get("poll_interval_seconds", 3600)  # 1 hour default
        self._on_bar_callback: Optional[Callable[[NormalizedAggregatedBar], Awaitable[None]]] = None

    def set_on_bar(self, callback: Callable[[NormalizedAggregatedBar], Awaitable[None]]) -> None:
        """Set callback for emitting pre-aggregated daily bars."""
        self._on_bar_callback = callback

    async def start(self) -> None:
        """Start the REST polling loop."""
        self._running = True
        logger.info("FMP connector starting for %d tickers (interval=%ds)", len(self._tickers), self._poll_interval)

        async with httpx.AsyncClient(timeout=15) as client:
            while self._running:
                await self._fetch_all(client)
                await asyncio.sleep(self._poll_interval)

    async def _fetch_all(self, client: httpx.AsyncClient) -> None:
        """Fetch latest quote for all tickers."""
        for ticker in self._tickers:
            if not self._running:
                break
            try:
                await self._fetch_quote(client, ticker)
            except Exception as e:
                logger.warning("FMP fetch failed for %s: %s", ticker, e)

    async def _fetch_quote(self, client: httpx.AsyncClient, ticker: str) -> None:
        """Fetch and emit a single ticker quote."""
        resp = await client.get(
            f"{FMP_BASE_URL}/quote/{ticker}",
            params={"apikey": self._api_key},
        )
        resp.raise_for_status()
        data = resp.json()

        if not data:
            logger.warning("FMP empty response for %s", ticker)
            return

        q = data[0]
        bar = NormalizedAggregatedBar(
            event_type=EventType.MARKET_BAR,
            symbol=ticker.replace(".JK", ""),
            timeframe="1d",
            open=float(q.get("open", 0)),
            high=float(q.get("dayHigh", 0)),
            low=float(q.get("dayLow", 0)),
            close=float(q.get("price", 0)),
            volume=int(q.get("volume", 0)),
            bar_close_utc=datetime.now(timezone.utc),
            source_provider="fmp",
        )

        if self._on_bar_callback:
            await self._on_bar_callback(bar)
            logger.debug("FMP emitted bar for %s: close=%.2f", bar.symbol, bar.close)

    async def stop(self) -> None:
        """Stop the connector."""
        self._running = False
        logger.info("FMP connector stopped")

    async def health_check(self) -> bool:
        """Check connector health."""
        return self._running
