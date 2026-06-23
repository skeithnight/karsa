"""YFinance EOD Connector — Sprint-61.

Batch-mode connector for IDX tickers via Yahoo Finance.
Fetches daily OHLCV bars after IDX market close (16:00 WIB / 09:00 UTC).
No API key required — scrapes Yahoo Finance.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from karsa.providers.application.connector_factory import BaseConnector, register_connector
from karsa.providers.domain.normalization import NormalizedAggregatedBar, EventType

logger = logging.getLogger(__name__)


@register_connector("yfinance")
class YFinanceConnector(BaseConnector):
    """YFinance EOD connector for IDX tickers.

    Batch mode — fetches daily OHLCV after market close.
    Uses set_on_bar callback to emit NormalizedAggregatedBar directly,
    bypassing the tick aggregation engine.
    """

    def __init__(self, provider_id: str, config: dict, credentials: dict):
        super().__init__(provider_id, config, credentials)
        self._tickers = config.get("tickers", [])
        self._schedule_hour_utc = config.get("schedule_hour_utc", 9)  # 16:00 WIB
        self._on_bar_callback: Optional[Callable[[NormalizedAggregatedBar], Awaitable[None]]] = None

    def set_on_bar(self, callback: Callable[[NormalizedAggregatedBar], Awaitable[None]]) -> None:
        """Set callback for emitting pre-aggregated daily bars."""
        self._on_bar_callback = callback

    async def start(self) -> None:
        """Start the scheduled EOD fetch loop."""
        self._running = True
        logger.info("YFinance connector starting for %d tickers", len(self._tickers))

        while self._running:
            now = datetime.now(timezone.utc)
            next_run = self._next_schedule_time(now)
            wait_seconds = (next_run - now).total_seconds()
            logger.info("YFinance next fetch in %.0f seconds (at %s)", wait_seconds, next_run.isoformat())
            await asyncio.sleep(wait_seconds)

            if self._running:
                await self._fetch_and_emit()

    async def _fetch_and_emit(self) -> None:
        """Fetch daily OHLCV for all tickers and emit bars."""
        try:
            import yfinance as yf
        except ImportError:
            logger.error("yfinance package not installed — run: uv add yfinance")
            return

        try:
            logger.info("YFinance downloading %d tickers...", len(self._tickers))
            data = yf.download(
                self._tickers,
                period="5d",
                group_by="ticker",
                progress=False,
            )

            for ticker in self._tickers:
                try:
                    df = data[ticker] if len(self._tickers) > 1 else data
                    row = df.dropna().iloc[-1]

                    bar = NormalizedAggregatedBar(
                        event_type=EventType.MARKET_BAR,
                        symbol=ticker.replace(".JK", ""),
                        timeframe="1d",
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=int(row["Volume"]),
                        bar_close_utc=datetime.now(timezone.utc),
                        source_provider="yfinance",
                    )

                    if self._on_bar_callback:
                        await self._on_bar_callback(bar)
                        logger.debug("YFinance emitted bar for %s: close=%.2f", bar.symbol, bar.close)

                except Exception as e:
                    logger.warning("YFinance failed for %s: %s", ticker, e)

            logger.info("YFinance fetch complete for %d tickers", len(self._tickers))

        except Exception as e:
            logger.error("YFinance batch download failed: %s", e)

    def _next_schedule_time(self, now: datetime) -> datetime:
        """Calculate the next scheduled run time."""
        target = now.replace(
            hour=self._schedule_hour_utc,
            minute=0,
            second=0,
            microsecond=0,
        )
        if now >= target:
            # Already past today's window, schedule for tomorrow
            from datetime import timedelta
            target += timedelta(days=1)
        return target

    async def stop(self) -> None:
        """Stop the connector."""
        self._running = False
        logger.info("YFinance connector stopped")

    async def health_check(self) -> bool:
        """Check connector health."""
        return self._running
