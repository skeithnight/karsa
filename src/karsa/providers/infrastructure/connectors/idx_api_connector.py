"""IDX-API SQLite Connector — Sprint-63.

Reads synced IDX data from a NeaByteLab/IDX-API SQLite database.
Emits NormalizedAggregatedBar for daily OHLCV and NormalizedNewsEvent
for company announcements.

The IDX-API pipeline must be run separately to populate the SQLite database
before this connector can read from it.
"""
import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, List, Optional, Tuple

from karsa.providers.application.connector_factory import BaseConnector, register_connector
from karsa.providers.domain.normalization import (
    EventType,
    NormalizedAggregatedBar,
    NormalizedNewsEvent,
)

logger = logging.getLogger(__name__)

# Default polling interval in seconds (check for new data every 60s)
DEFAULT_POLL_INTERVAL = 60


@register_connector("idx_api")
class IDXAPIConnector(BaseConnector):
    """IDX-API SQLite connector for Indonesian Stock Exchange data.

    Reads from a synced SQLite database produced by the NeaByteLab/IDX-API
    Deno pipeline. Supports daily OHLCV bars and company announcements.

    Config keys:
        db_path: str — Absolute path to the SQLite database file.
        tickers: list[str] — IDX ticker codes to watch (e.g. ["BBCA", "BBRI"]).
        poll_interval: int — Seconds between polling cycles (default 60).
    """

    def __init__(self, provider_id: str, config: dict, credentials: dict):
        super().__init__(provider_id, config, credentials)
        self._db_path: str = config.get("db_path", "")
        self._tickers: List[str] = config.get("tickers", [])
        self._poll_interval: int = config.get("poll_interval", DEFAULT_POLL_INTERVAL)
        self._on_bar_callback: Optional[Callable[[NormalizedAggregatedBar], Awaitable[None]]] = None
        self._on_news_callback: Optional[Callable[[NormalizedNewsEvent], Awaitable[None]]] = None
        self._last_seen_date: Optional[int] = None  # Track latest processed date (YYYYMMDD)
        self._last_announcement_id: Optional[str] = None  # Track latest announcement

    # -- Callback setters ---------------------------------------------------

    def set_on_bar(self, callback: Callable[[NormalizedAggregatedBar], Awaitable[None]]) -> None:
        """Set callback for emitting pre-aggregated daily OHLCV bars."""
        self._on_bar_callback = callback

    def set_on_news(self, callback: Callable[[NormalizedNewsEvent], Awaitable[None]]) -> None:
        """Set callback for emitting company announcement events."""
        self._on_news_callback = callback

    # -- Lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        """Start the polling loop that reads new data from SQLite."""
        self._running = True
        self._validate_config()

        logger.info(
            "IDX-API connector starting — db=%s, tickers=%d, poll=%ds",
            self._db_path,
            len(self._tickers),
            self._poll_interval,
        )

        while self._running:
            try:
                await self._poll_cycle()
            except Exception:
                logger.exception("IDX-API poll cycle failed")

            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> None:
        """Stop the connector."""
        self._running = False
        logger.info("IDX-API connector stopped")

    async def health_check(self) -> bool:
        """Check connector health by verifying database is accessible."""
        if not self._running:
            return False
        try:
            conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
            conn.execute("SELECT 1 FROM stock_summary LIMIT 1")
            conn.close()
            return True
        except Exception:
            logger.warning("IDX-API health check failed — db not accessible")
            return False

    # -- Internal -----------------------------------------------------------

    def _validate_config(self) -> None:
        """Validate required configuration."""
        if not self._db_path:
            raise ValueError("IDX-API connector requires 'db_path' in config")
        if not Path(self._db_path).exists():
            raise FileNotFoundError(f"IDX-API database not found: {self._db_path}")
        if not self._tickers:
            logger.warning("IDX-API connector has no tickers configured — will emit nothing")

    def _connect(self) -> sqlite3.Connection:
        """Open a read-only SQLite connection."""
        return sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)

    async def _poll_cycle(self) -> None:
        """Single polling cycle: fetch data in thread, emit from async context."""
        # Fetch new OHLCV bars
        bars = await asyncio.to_thread(self._query_new_bars)
        for bar in bars:
            if self._on_bar_callback:
                await self._on_bar_callback(bar)
                logger.debug("IDX-API emitted bar for %s: close=%.2f", bar.symbol, bar.close)
        if bars:
            logger.info("IDX-API emitted %d bar(s)", len(bars))

        # Fetch new announcements
        news = await asyncio.to_thread(self._query_new_announcements)
        for event in news:
            if self._on_news_callback:
                await self._on_news_callback(event)
                logger.debug("IDX-API emitted announcement for %s", event.tickers)
        if news:
            logger.info("IDX-API emitted %d announcement(s)", len(news))

    # -- OHLCV bars ---------------------------------------------------------

    def _query_new_bars(self) -> List[NormalizedAggregatedBar]:
        """Query stock_summary for new daily OHLCV data. Returns bars list."""
        if not self._tickers:
            return []

        conn = self._connect()
        try:
            cursor = conn.cursor()

            placeholders = ",".join("?" for _ in self._tickers)
            query = f"""
                SELECT code, date, open, high, low, close, volume
                FROM stock_summary
                WHERE code IN ({placeholders})
            """
            params: list = list(self._tickers)

            if self._last_seen_date is not None:
                query += " AND date > ?"
                params.append(self._last_seen_date)

            query += " ORDER BY date ASC"
            cursor.execute(query, params)
            rows = cursor.fetchall()

            if not rows:
                return []

            bars: List[NormalizedAggregatedBar] = []
            max_date = self._last_seen_date

            for code, date_int, open_p, high_p, low_p, close_p, volume in rows:
                if any(v is None for v in (open_p, high_p, low_p, close_p)):
                    logger.debug("Skipping %s on %s — missing price data", code, date_int)
                    continue

                bar = NormalizedAggregatedBar(
                    event_type=EventType.MARKET_BAR,
                    symbol=code,
                    timeframe="1d",
                    open=float(open_p),
                    high=float(high_p),
                    low=float(low_p),
                    close=float(close_p),
                    volume=int(volume or 0),
                    bar_close_utc=self._date_int_to_utc(date_int),
                    source_provider="idx_api",
                )
                bars.append(bar)

                if max_date is None or date_int > max_date:
                    max_date = date_int

            self._last_seen_date = max_date
            return bars

        finally:
            conn.close()

    # -- Company announcements ----------------------------------------------

    def _query_new_announcements(self) -> List[NormalizedNewsEvent]:
        """Query company_announcement for new announcements. Returns events list."""
        if not self._tickers:
            return []

        conn = self._connect()
        try:
            cursor = conn.cursor()

            placeholders = ",".join("?" for _ in self._tickers)
            query = f"""
                SELECT id, title, date, company_code, type, subject, attachments
                FROM company_announcement
                WHERE company_code IN ({placeholders})
            """
            params: list = list(self._tickers)

            if self._last_announcement_id is not None:
                query += " AND id > ?"
                params.append(self._last_announcement_id)

            query += " ORDER BY date DESC, id DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()

            if not rows:
                return []

            events: List[NormalizedNewsEvent] = []
            newest_id = self._last_announcement_id

            for ann_id, title, date_int, company_code, ann_type, subject, attachments_json in rows:
                url = ""
                if attachments_json:
                    try:
                        attachments = json.loads(attachments_json)
                        if isinstance(attachments, list) and attachments:
                            url = attachments[0].get("url", "")
                    except (json.JSONDecodeError, TypeError):
                        pass

                published_at = self._date_int_to_utc(date_int) if date_int else datetime.now(timezone.utc)

                event = NormalizedNewsEvent(
                    event_type=EventType.NEWS_ARTICLE,
                    headline=title or "",
                    url=url,
                    tickers=[company_code] if company_code else [],
                    sentiment_score=None,
                    published_at=published_at,
                    source_provider="idx_api",
                )
                events.append(event)

                if newest_id is None or ann_id > newest_id:
                    newest_id = ann_id

            self._last_announcement_id = newest_id
            return events

        finally:
            conn.close()

    # -- Utilities ----------------------------------------------------------

    @staticmethod
    def _date_int_to_utc(date_int: int) -> datetime:
        """Convert YYYYMMDD integer to a UTC datetime.

        IDX-API stores dates as Unix timestamps in milliseconds.
        """
        # Handle both Unix timestamp (ms) and YYYYMMDD integer formats
        if date_int > 99999999:
            # Unix timestamp in milliseconds
            return datetime.fromtimestamp(date_int / 1000, tz=timezone.utc)
        else:
            # YYYYMMDD format
            date_str = str(date_int)
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            # Market close: 16:00 WIB = 09:00 UTC
            return datetime(year, month, day, 9, 0, 0, tzinfo=timezone.utc)
