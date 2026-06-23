"""Durable Bar Buffer — SQLite WAL-backed persistence for market data bars.

Prevents data loss on crash by writing every emitted bar to a local
SQLite database before forwarding to the event emitter. On restart,
pending (unflushed) bars are replayed.

Uses SQLite WAL mode for concurrent read/write without blocking.
"""
import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from karsa.providers.domain.normalization import NormalizedAggregatedBar, NormalizedNewsEvent

logger = logging.getLogger(__name__)

# Default buffer path — override via DURABLE_BUFFER_PATH env var
DEFAULT_BUFFER_PATH = "/tmp/karsa/bar_buffer.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pending_bars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    flushed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pending_news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    flushed INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_pending_bars_flushed ON pending_bars(flushed);
CREATE INDEX IF NOT EXISTS idx_pending_news_flushed ON pending_news(flushed);
"""

FLUSH_BATCH_SIZE = 500


class DurableBarBuffer:
    """SQLite WAL-backed buffer for bars and news events.

    Every bar/news is written to SQLite before being forwarded.
    On crash recovery, unflushed entries are replayed.

    The buffer is self-cleaning: flushed rows are deleted periodically.
    Writes are batched — commit() fires every COMMIT_INTERVAL writes
    to avoid per-write fsync overhead during high throughput.
    """

    COMMIT_INTERVAL = 50  # Commit every N writes

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or os.environ.get("DURABLE_BUFFER_PATH", DEFAULT_BUFFER_PATH)
        self._conn: Optional[sqlite3.Connection] = None
        self._pending_writes = 0

    def _ensure_dir(self) -> None:
        """Create parent directory if it doesn't exist."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

    def open(self) -> None:
        """Open the SQLite database and initialize schema."""
        self._ensure_dir()
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()
        logger.info(f"DurableBarBuffer opened: {self._db_path}")

    def close(self) -> None:
        """Flush pending writes and close the database connection."""
        self.flush()
        if self._conn:
            self._conn.close()
            self._conn = None

    def write_bar(self, bar: NormalizedAggregatedBar) -> None:
        """Write a bar to the durable buffer (batched commit)."""
        if not self._conn:
            return
        payload = json.dumps({
            "symbol": bar.symbol,
            "timeframe": bar.timeframe,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
            "bar_close_utc": bar.bar_close_utc.isoformat(),
            "source_provider": bar.source_provider,
        })
        self._conn.execute(
            "INSERT INTO pending_bars (payload) VALUES (?)",
            (payload,)
        )
        self._pending_writes += 1
        if self._pending_writes >= self.COMMIT_INTERVAL:
            self._conn.commit()
            self._pending_writes = 0

    def write_news(self, news: NormalizedNewsEvent) -> None:
        """Write a news event to the durable buffer (batched commit)."""
        if not self._conn:
            return
        payload = json.dumps({
            "headline": news.headline,
            "url": news.url,
            "tickers": news.tickers,
            "sentiment_score": news.sentiment_score,
            "published_at": news.published_at.isoformat(),
            "source_provider": news.source_provider,
        })
        self._conn.execute(
            "INSERT INTO pending_news (payload) VALUES (?)",
            (payload,)
        )
        self._pending_writes += 1
        if self._pending_writes >= self.COMMIT_INTERVAL:
            self._conn.commit()
            self._pending_writes = 0

    def flush(self) -> None:
        """Force-commit any pending writes. Call on shutdown."""
        if self._conn and self._pending_writes > 0:
            self._conn.commit()
            self._pending_writes = 0

    def replay_unflushed_bars(self) -> List[NormalizedAggregatedBar]:
        """Read all unflushed bars (crash recovery). Returns them in order."""
        if not self._conn:
            return []
        cursor = self._conn.execute(
            "SELECT id, payload FROM pending_bars WHERE flushed = 0 ORDER BY id"
        )
        bars = []
        for row in cursor:
            data = json.loads(row[1])
            bars.append(NormalizedAggregatedBar(
                symbol=data["symbol"],
                timeframe=data["timeframe"],
                open=data["open"],
                high=data["high"],
                low=data["low"],
                close=data["close"],
                volume=data["volume"],
                bar_close_utc=datetime.fromisoformat(data["bar_close_utc"]),
                source_provider=data["source_provider"],
            ))
        return bars

    def replay_unflushed_news(self) -> List[NormalizedNewsEvent]:
        """Read all unflushed news events (crash recovery)."""
        if not self._conn:
            return []
        cursor = self._conn.execute(
            "SELECT id, payload FROM pending_news WHERE flushed = 0 ORDER BY id"
        )
        events = []
        for row in cursor:
            data = json.loads(row[1])
            events.append(NormalizedNewsEvent(
                headline=data["headline"],
                url=data["url"],
                tickers=data["tickers"],
                sentiment_score=data.get("sentiment_score"),
                published_at=datetime.fromisoformat(data["published_at"]),
                source_provider=data["source_provider"],
            ))
        return events

    def mark_bars_flushed(self, count: int) -> None:
        """Mark the oldest N unflushed bars as flushed."""
        if not self._conn:
            return
        self._conn.execute(
            "UPDATE pending_bars SET flushed = 1 WHERE id IN "
            "(SELECT id FROM pending_bars WHERE flushed = 0 ORDER BY id LIMIT ?)",
            (count,)
        )
        self._conn.commit()

    def mark_news_flushed(self, count: int) -> None:
        """Mark the oldest N unflushed news events as flushed."""
        if not self._conn:
            return
        self._conn.execute(
            "UPDATE pending_news SET flushed = 1 WHERE id IN "
            "(SELECT id FROM pending_news WHERE flushed = 0 ORDER BY id LIMIT ?)",
            (count,)
        )
        self._conn.commit()

    def cleanup_flushed(self, max_age_hours: int = 24) -> int:
        """Delete flushed rows older than max_age_hours. Returns count deleted."""
        if not self._conn:
            return 0
        cur_bars = self._conn.execute(
            "DELETE FROM pending_bars WHERE flushed = 1 AND created_at < datetime('now', ?)",
            (f"-{max_age_hours} hours",)
        )
        cur_news = self._conn.execute(
            "DELETE FROM pending_news WHERE flushed = 1 AND created_at < datetime('now', ?)",
            (f"-{max_age_hours} hours",)
        )
        self._conn.commit()
        deleted = cur_bars.rowcount + cur_news.rowcount
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} flushed buffer rows")
        return deleted

    @property
    def pending_bar_count(self) -> int:
        """Count of unflushed bars."""
        if not self._conn:
            return 0
        row = self._conn.execute(
            "SELECT COUNT(*) FROM pending_bars WHERE flushed = 0"
        ).fetchone()
        return row[0] if row else 0

    @property
    def pending_news_count(self) -> int:
        """Count of unflushed news events."""
        if not self._conn:
            return 0
        row = self._conn.execute(
            "SELECT COUNT(*) FROM pending_news WHERE flushed = 0"
        ).fetchone()
        return row[0] if row else 0
