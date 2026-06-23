"""Alpha Vantage Connector — Sprint-61.

REST polling connector with aggressive rate limiting (25 req/day free tier).
IDX tickers use .IDX suffix (e.g., BBCA.IDX) — different from YFinance/FMP.
Provides daily OHLCV + technical indicators.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

import httpx

from karsa.providers.application.connector_factory import BaseConnector, register_connector
from karsa.providers.domain.normalization import NormalizedAggregatedBar, EventType

logger = logging.getLogger(__name__)

AV_BASE_URL = "https://www.alphavantage.co/query"


@register_connector("alpha_vantage")
class AlphaVantageConnector(BaseConnector):
    """Alpha Vantage connector for daily OHLCV data.

    REST polling with per-ticker rate limiting.
    Free tier: 25 req/day — uses conservative 3s delay between tickers.
    IDX suffix: .IDX (not .JK like YFinance/FMP).
    """

    IDX_SUFFIX = ".IDX"

    def __init__(self, provider_id: str, config: dict, credentials: dict):
        super().__init__(provider_id, config, credentials)
        self._api_key = credentials.get("api_key", "")
        self._tickers = config.get("tickers", [])  # ["BBCA", "BBRI", ...] — suffix added automatically
        self._poll_interval = config.get("poll_interval_seconds", 7200)  # 2 hours default
        self._per_ticker_delay = config.get("per_ticker_delay_seconds", 3)
        self._on_bar_callback: Optional[Callable[[NormalizedAggregatedBar], Awaitable[None]]] = None

    def set_on_bar(self, callback: Callable[[NormalizedAggregatedBar], Awaitable[None]]) -> None:
        """Set callback for emitting pre-aggregated daily bars."""
        self._on_bar_callback = callback

    async def start(self) -> None:
        """Start the REST polling loop with rate limiting."""
        self._running = True
        logger.info(
            "Alpha Vantage connector starting for %d tickers (interval=%ds, delay=%ds)",
            len(self._tickers), self._poll_interval, self._per_ticker_delay,
        )

        async with httpx.AsyncClient(timeout=20) as client:
            while self._running:
                for ticker in self._tickers:
                    if not self._running:
                        break
                    try:
                        await self._fetch_daily(client, ticker)
                    except Exception as e:
                        logger.warning("Alpha Vantage fetch failed for %s: %s", ticker, e)
                    await asyncio.sleep(self._per_ticker_delay)

                logger.info("Alpha Vantage cycle complete, next in %ds", self._poll_interval)
                await asyncio.sleep(self._poll_interval)

    async def _fetch_daily(self, client: httpx.AsyncClient, ticker: str) -> None:
        """Fetch daily time series for a single ticker."""
        symbol = f"{ticker}{self.IDX_SUFFIX}"
        resp = await client.get(
            AV_BASE_URL,
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact",
                "apikey": self._api_key,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        # Check for rate limit or error responses
        if "Error Message" in data:
            logger.warning("Alpha Vantage error for %s: %s", symbol, data["Error Message"])
            return
        if "Note" in data:
            logger.warning("Alpha Vantage rate limited: %s", data["Note"])
            return

        ts = data.get("Time Series (Daily)", {})
        if not ts:
            logger.warning("Alpha Vantage no time series data for %s", symbol)
            return

        latest_date = sorted(ts.keys())[-1]
        row = ts[latest_date]

        bar = NormalizedAggregatedBar(
            event_type=EventType.MARKET_BAR,
            symbol=ticker,  # Already without suffix
            timeframe="1d",
            open=float(row["1. open"]),
            high=float(row["2. high"]),
            low=float(row["3. low"]),
            close=float(row["4. close"]),
            volume=int(row["5. volume"]),
            bar_close_utc=datetime.now(timezone.utc),
            source_provider="alpha_vantage",
        )

        if self._on_bar_callback:
            await self._on_bar_callback(bar)
            logger.debug("Alpha Vantage emitted bar for %s: close=%.2f", bar.symbol, bar.close)

    async def stop(self) -> None:
        """Stop the connector."""
        self._running = False
        logger.info("Alpha Vantage connector stopped")

    async def health_check(self) -> bool:
        """Check connector health."""
        return self._running
