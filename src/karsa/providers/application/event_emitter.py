"""Event Emitter — routes normalized events to in-process callbacks and logs.

Market data (bars, news) flows through in-process callbacks, NOT through
the PostgresEventBus (which is for domain events only). Downstream
consumers (AI agents, projection workers) will receive data via a
message broker in future sprints.

Sprint-52: Tracks emit counts for observability.
"""
import logging
from typing import Any, Callable, Awaitable, Optional

from karsa.providers.domain.normalization import (
    NormalizedMarketTick,
    NormalizedAggregatedBar,
    NormalizedNewsEvent,
    EventType,
)

logger = logging.getLogger(__name__)

# Topic constants
TOPIC_MARKET_BAR = "karsa.market.bar"
TOPIC_NEWS_ARTICLE = "karsa.news.article"
TOPIC_MARKET_RAW = "karsa.market.raw"


class DataBridgeEventEmitter:
    """Routes normalized events and tracks emission counts.

    Market data events are logged and counted. In future sprints,
    this will publish to a message broker (Kafka/Redis) for
    downstream consumers.
    """

    def __init__(self, event_bus=None):
        self._event_bus = event_bus  # Reserved for future domain event publishing
        self._bar_count = 0
        self._news_count = 0
        self._tick_count = 0

    async def emit_bar(self, bar: NormalizedAggregatedBar) -> None:
        """Emit an aggregated bar."""
        self._bar_count += 1
        if self._bar_count % 100 == 1:  # Log every 100th bar to reduce noise
            logger.info(
                f"Bar #{self._bar_count}: {bar.symbol} {bar.timeframe} "
                f"O={bar.open:.2f} H={bar.high:.2f} L={bar.low:.2f} C={bar.close:.2f} V={bar.volume}"
            )

    async def emit_news(self, news: NormalizedNewsEvent) -> None:
        """Emit a news article."""
        self._news_count += 1
        logger.info(
            f"News #{self._news_count}: {news.headline[:80]}... "
            f"tickers={news.tickers} sentiment={news.sentiment_score}"
        )

    async def emit_tick(self, tick: NormalizedMarketTick) -> None:
        """Emit a raw tick (internal, consumed by aggregation)."""
        self._tick_count += 1

    @property
    def bar_count(self) -> int:
        return self._bar_count

    @property
    def news_count(self) -> int:
        return self._news_count

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def emit_count(self) -> int:
        return self._bar_count + self._news_count + self._tick_count
