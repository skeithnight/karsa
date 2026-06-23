"""Gap Fill Service — REST-based historical bar recovery.

Sprint-53: Fetches missing bars from provider REST API
after WebSocket reconnection to fill data gaps.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Callable, Awaitable

import httpx

from karsa.providers.domain.normalization import NormalizedAggregatedBar
from karsa.providers.events.events import GapFillCompletedEvent
from karsa.memory.infrastructure.event.postgres_event_bus import PostgresEventBus

logger = logging.getLogger(__name__)

# Polygon REST API for historical bars
POLYGON_BARS_URL = "https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start}/{end}"


class GapFillService:
    """Fetches missing historical bars via REST API after reconnection.

    Supports retry with exponential backoff. Emits GapFillCompletedEvent
    on successful recovery.
    """

    def __init__(
        self,
        event_bus: PostgresEventBus,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ):
        self._event_bus = event_bus
        self._max_retries = max_retries
        self._base_delay = base_delay

    async def fill_gap_polygon(
        self,
        symbol: str,
        timeframe: str,
        gap_start: datetime,
        gap_end: datetime,
        api_key: str,
        on_bar: Optional[Callable[[NormalizedAggregatedBar], Awaitable[None]]] = None,
    ) -> List[NormalizedAggregatedBar]:
        """Fill a data gap using Polygon REST API.

        Args:
            symbol: Ticker symbol.
            timeframe: Bar timeframe ("1m", "5m", etc.).
            gap_start: Start of the gap.
            gap_end: End of the gap.
            api_key: Polygon API key.
            on_bar: Optional callback for each recovered bar.

        Returns:
            List of recovered bars.
        """
        multiplier, timespan = self._parse_timeframe(timeframe)
        url = POLYGON_BARS_URL.format(
            symbol=symbol,
            multiplier=multiplier,
            timespan=timespan,
            start=gap_start.strftime("%Y-%m-%dT%H:%M:%S"),
            end=gap_end.strftime("%Y-%m-%dT%H:%M:%S"),
        )

        bars = []
        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(
                        url,
                        params={"apiKey": api_key, "adjusted": "true", "limit": 5000},
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    for result in data.get("results", []):
                        bar = NormalizedAggregatedBar(
                            symbol=symbol,
                            timeframe=timeframe,
                            open=result.get("o", 0),
                            high=result.get("h", 0),
                            low=result.get("l", 0),
                            close=result.get("c", 0),
                            volume=int(result.get("v", 0)),
                            bar_close_utc=datetime.fromtimestamp(
                                result.get("t", 0) / 1000, tz=timezone.utc
                            ),
                            source_provider="polygon",
                        )
                        bars.append(bar)
                        if on_bar:
                            await on_bar(bar)

                    logger.info(f"Gap filled: {len(bars)} bars for {symbol} ({timeframe})")

                    # Emit completion event
                    await self._event_bus.async_publish(GapFillCompletedEvent(
                        provider_id="polygon",
                        symbol=symbol,
                        timeframe=timeframe,
                        bars_filled=len(bars),
                        gap_start=gap_start.isoformat(),
                        gap_end=gap_end.isoformat(),
                    ))
                    return bars

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limited — wait and retry
                    delay = self._base_delay * (2 ** attempt)
                    logger.warning(f"Polygon rate limited, retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Polygon API error ({e.response.status_code}): {e}")
                    break
            except Exception as e:
                delay = self._base_delay * (2 ** attempt)
                logger.error(f"Gap fill attempt {attempt + 1} failed: {e}")
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(delay)

        logger.error(f"Gap fill failed after {self._max_retries} attempts for {symbol}")
        return bars

    def _parse_timeframe(self, timeframe: str) -> tuple:
        """Parse timeframe string to (multiplier, timespan) for Polygon API."""
        mapping = {
            "1m": (1, "minute"),
            "5m": (5, "minute"),
            "15m": (15, "minute"),
            "1h": (1, "hour"),
        }
        return mapping.get(timeframe, (1, "minute"))
