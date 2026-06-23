"""Finnhub REST polling connector for news articles.

Sprint-52: Polls Finnhub news API at configured intervals.
Registered as 'finnhub' in the ConnectorFactory.
"""
import asyncio
import logging
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, Awaitable, List

import httpx

from karsa.providers.application.connector_factory import BaseConnector, register_connector
from karsa.providers.domain.normalization import NormalizedNewsEvent, EventType, DeadLetterEntry
from karsa.providers.infrastructure.storage.dead_letter_repository import DeadLetterRepository

logger = logging.getLogger(__name__)

FINNHUB_NEWS_URL = "https://finnhub.io/api/v1/news"


@register_connector("finnhub")
class FinnhubConnector(BaseConnector):
    """Finnhub REST polling connector for news articles.

    Polls the Finnhub general news endpoint at a configurable interval,
    filters by category, and emits NormalizedNewsEvent objects.
    """

    def __init__(self, provider_id: str, config: Dict[str, Any], credentials: Dict[str, str], dead_letter_repo: Optional[DeadLetterRepository] = None):
        super().__init__(provider_id, config, credentials)
        self._task: Optional[asyncio.Task] = None
        self._on_news: Optional[Callable[[NormalizedNewsEvent], Awaitable[None]]] = None
        self._dead_letter_repo = dead_letter_repo
        self._poll_interval = config.get("poll_interval_seconds", 60)
        self._category = config.get("category", "general")
        self._min_sentiment = config.get("min_sentiment", -1.0)
        # OrderedDict for deterministic LRU pruning (insertion-ordered)
        self._seen_ids: OrderedDict[str, bool] = OrderedDict()
        self._max_seen_ids = 10000
        self._client: Optional[httpx.AsyncClient] = None
        # Health check cache to avoid burning rate limit
        self._last_health_check: Optional[float] = None
        self._last_health_result: bool = False
        self._health_cache_ttl = config.get("health_cache_ttl_seconds", 300)

    def set_on_news(self, callback: Callable[[NormalizedNewsEvent], Awaitable[None]]) -> None:
        """Set the callback for incoming news articles."""
        self._on_news = callback

    async def start(self) -> None:
        """Start the polling loop."""
        self._running = True
        self._client = httpx.AsyncClient(timeout=30.0)
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"FinnhubConnector started (interval={self._poll_interval}s, category={self._category})")

    async def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False
        # Cancel task first (unblocks the sleep in _poll_loop)
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        # Then close HTTP client
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None
        logger.info("FinnhubConnector stopped")

    async def reset(self) -> None:
        """Reset internal state for supervised restart."""
        await self.stop()
        self._seen_ids.clear()
        self._last_health_check = None
        self._last_health_result = False
        logger.info("FinnhubConnector reset for restart")

    async def health_check(self) -> bool:
        """Check if the connector is running and can reach Finnhub.

        Results are cached for health_cache_ttl_seconds (default 5min)
        to avoid burning the API rate limit on health pings alone.
        """
        if not self._running or not self._client:
            return False

        now = time.monotonic()
        if self._last_health_check is not None:
            elapsed = now - self._last_health_check
            if elapsed < self._health_cache_ttl:
                return self._last_health_result

        try:
            resp = await self._client.get(
                FINNHUB_NEWS_URL,
                params={"category": "general", "token": self.credentials.get("api_key", "")},
            )
            self._last_health_result = resp.status_code == 200
        except Exception:
            self._last_health_result = False

        self._last_health_check = now
        return self._last_health_result

    async def _poll_loop(self) -> None:
        """Main polling loop with error recovery."""
        while self._running:
            try:
                await self._fetch_and_emit()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"FinnhubConnector poll error: {e}")
            await asyncio.sleep(self._poll_interval)

    async def _fetch_and_emit(self) -> None:
        """Fetch news from Finnhub and emit normalized events."""
        if not self._client:
            return

        api_key = self.credentials.get("api_key", "")
        resp = await self._client.get(
            FINNHUB_NEWS_URL,
            params={"category": self._category, "token": api_key},
        )
        resp.raise_for_status()
        articles = resp.json()

        for article in articles:
            article_id = article.get("id")
            if article_id in self._seen_ids:
                continue
            self._seen_ids[article_id] = True

            news_event = self._normalize_article(article)
            if news_event and self._on_news:
                await self._on_news(news_event)

        # Deterministic LRU pruning — evict oldest entries (FIFO)
        while len(self._seen_ids) > self._max_seen_ids:
            self._seen_ids.popitem(last=False)

    def _normalize_article(self, article: dict) -> Optional[NormalizedNewsEvent]:
        """Normalize a Finnhub news article to NormalizedNewsEvent."""
        try:
            headline = article.get("headline", "").strip()
            if not headline:
                return None

            # Extract tickers from related symbols
            tickers = article.get("related", "")
            if isinstance(tickers, str):
                tickers = [t.strip() for t in tickers.split(",") if t.strip()]

            # Sentiment score (Finnhub provides this in some endpoints)
            sentiment = article.get("sentiment")
            if sentiment is not None:
                sentiment = float(sentiment)

            published_at = datetime.fromtimestamp(
                article.get("datetime", 0), tz=timezone.utc
            )

            return NormalizedNewsEvent(
                headline=headline,
                url=article.get("url", ""),
                tickers=tickers,
                sentiment_score=sentiment,
                published_at=published_at,
                source_provider="finnhub",
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"Finnhub normalization error: {e} | raw: {article}")
            if self._dead_letter_repo:
                try:
                    self._dead_letter_repo.append(DeadLetterEntry(
                        provider_id=self.provider_id,
                        raw_payload=article,
                        error_message=str(e),
                        error_type="TYPE_COERCION",
                    ))
                except Exception as dl_err:
                    logger.error(f"Dead letter write failed: {dl_err}")
            return None
