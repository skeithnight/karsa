"""Aggregation Engine — ticks to OHLCV bars.

Sprint-52: Buffers raw ticks in memory and emits standardized
OHLCV bars when time windows close. Prevents token budget
exhaustion by avoiding raw tick streaming to LLMs.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Callable, Awaitable

from karsa.providers.domain.normalization import NormalizedMarketTick, NormalizedAggregatedBar

logger = logging.getLogger(__name__)

# Supported timeframes and their durations
TIMEFRAME_DURATIONS = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
}


class TickBuffer:
    """In-memory buffer for a single symbol+timeframe window."""

    MAX_TICKS = 10000  # Safety cap to prevent OOM during market hours

    def __init__(self, symbol: str, timeframe: str, window_start: datetime):
        self.symbol = symbol
        self.timeframe = timeframe
        self.window_start = window_start
        self.ticks: List[NormalizedMarketTick] = []

    def add_tick(self, tick: NormalizedMarketTick) -> None:
        if len(self.ticks) >= self.MAX_TICKS:
            logger.warning(
                f"Buffer overflow: {self.symbol}_{self.timeframe} "
                f"reached {self.MAX_TICKS} ticks — dropping"
            )
            return
        self.ticks.append(tick)

    def is_empty(self) -> bool:
        return len(self.ticks) == 0

    def compute_bar(self, source_provider: str) -> Optional[NormalizedAggregatedBar]:
        """Compute OHLCV bar from buffered ticks."""
        if not self.ticks:
            return None

        prices = [t.price for t in self.ticks]
        volumes = [t.volume for t in self.ticks]
        duration = TIMEFRAME_DURATIONS.get(self.timeframe, timedelta(minutes=1))

        return NormalizedAggregatedBar(
            symbol=self.symbol,
            timeframe=self.timeframe,
            open=prices[0],
            high=max(prices),
            low=min(prices),
            close=prices[-1],
            volume=sum(volumes),
            bar_close_utc=self.window_start + duration,
            source_provider=source_provider,
        )


class AggregationEngine:
    """Buffers raw ticks and emits OHLCV bars on window close.

    Maintains an in-memory dictionary keyed by `{symbol}_{timeframe}`.
    When a time window closes, calculates OHLCV and emits the bar.
    """

    def __init__(
        self,
        timeframes: Optional[List[str]] = None,
        on_bar: Optional[Callable[[NormalizedAggregatedBar], Awaitable[None]]] = None,
    ):
        self._timeframes = timeframes or ["1m"]
        self._on_bar = on_bar
        # Key: "SYMBOL_TIMEFRAME" -> TickBuffer
        self._buffers: Dict[str, TickBuffer] = {}
        self._bar_count = 0

    def set_on_bar(self, callback: Callable[[NormalizedAggregatedBar], Awaitable[None]]) -> None:
        """Set the callback for emitted bars."""
        self._on_bar = callback

    async def process_tick(self, tick: NormalizedMarketTick) -> None:
        """Process an incoming tick — buffer it and check for window close."""
        for tf in self._timeframes:
            key = f"{tick.symbol}_{tf}"
            window_start = self._get_window_start(tick.timestamp_utc, tf)

            buffer = self._buffers.get(key)
            if buffer is None or buffer.window_start != window_start:
                # Window changed — emit old bar if exists, create new buffer
                if buffer and not buffer.is_empty():
                    await self._emit_bar(buffer)
                buffer = TickBuffer(tick.symbol, tf, window_start)
                self._buffers[key] = buffer

            buffer.add_tick(tick)

    async def flush_all(self) -> None:
        """Flush all pending buffers (e.g., on shutdown)."""
        for key, buffer in self._buffers.items():
            if not buffer.is_empty():
                await self._emit_bar(buffer)
        self._buffers.clear()

    def evict_stale_buffers(self, max_age_seconds: int = 300) -> int:
        """Remove buffers older than max_age_seconds.

        Prevents memory leaks when ticks stop arriving for a symbol.
        Returns the number of evicted buffers.
        """
        now = datetime.now(timezone.utc)
        stale_keys = []
        for key, buffer in self._buffers.items():
            duration = TIMEFRAME_DURATIONS.get(buffer.timeframe, timedelta(minutes=1))
            if now - buffer.window_start > duration * 2:
                stale_keys.append(key)
        for key in stale_keys:
            del self._buffers[key]
        if stale_keys:
            logger.info(f"Evicted {len(stale_keys)} stale aggregation buffers")
        return len(stale_keys)

    async def fill_gap(
        self,
        symbol: str,
        timeframe: str,
        bars: List[NormalizedAggregatedBar],
    ) -> None:
        """Process gap-filled bars from REST API recovery."""
        for bar in bars:
            if self._on_bar:
                await self._on_bar(bar)
            self._bar_count += 1
        logger.info(f"Gap filled: {len(bars)} bars for {symbol} ({timeframe})")

    def _get_window_start(self, timestamp: datetime, timeframe: str) -> datetime:
        """Calculate the window start time for a given timestamp."""
        duration = TIMEFRAME_DURATIONS.get(timeframe, timedelta(minutes=1))
        # Floor to window boundary
        if timeframe == "1m":
            return timestamp.replace(second=0, microsecond=0)
        elif timeframe == "5m":
            minute = (timestamp.minute // 5) * 5
            return timestamp.replace(minute=minute, second=0, microsecond=0)
        elif timeframe == "15m":
            minute = (timestamp.minute // 15) * 15
            return timestamp.replace(minute=minute, second=0, microsecond=0)
        elif timeframe == "1h":
            return timestamp.replace(minute=0, second=0, microsecond=0)
        return timestamp.replace(second=0, microsecond=0)

    async def _emit_bar(self, buffer: TickBuffer) -> None:
        """Compute and emit an OHLCV bar."""
        bar = buffer.compute_bar(source_provider="aggregation_engine")
        if bar and self._on_bar:
            await self._on_bar(bar)
            self._bar_count += 1
            logger.debug(
                f"Bar emitted: {bar.symbol} {bar.timeframe} "
                f"O={bar.open} H={bar.high} L={bar.low} C={bar.close} V={bar.volume}"
            )

    @property
    def bar_count(self) -> int:
        return self._bar_count
