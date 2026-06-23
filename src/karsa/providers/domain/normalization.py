"""Normalization models — unified Pydantic schemas for market data.

Sprint-52: Vendor-agnostic models that downstream consumers (AI agents,
projection workers) see. All vendor payloads are translated to these.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    MARKET_TICK = "MARKET_TICK"
    MARKET_BAR = "MARKET_BAR"
    NEWS_ARTICLE = "NEWS_ARTICLE"


class NormalizedMarketTick(BaseModel):
    """Unified tick model — single trade/quote update."""
    model_config = ConfigDict(frozen=True)

    event_type: EventType = Field(default=EventType.MARKET_TICK)
    symbol: str
    price: float
    volume: int
    timestamp_utc: datetime
    source_provider: str


class NormalizedAggregatedBar(BaseModel):
    """OHLCV bar — aggregated from raw ticks over a time window."""
    model_config = ConfigDict(frozen=True)

    event_type: EventType = Field(default=EventType.MARKET_BAR)
    symbol: str
    timeframe: str  # "1m", "5m", "1h"
    open: float
    high: float
    low: float
    close: float
    volume: int
    bar_close_utc: datetime
    source_provider: str


class NormalizedNewsEvent(BaseModel):
    """Unified news article model."""
    model_config = ConfigDict(frozen=True)

    event_type: EventType = Field(default=EventType.NEWS_ARTICLE)
    headline: str
    url: str
    tickers: List[str]
    sentiment_score: Optional[float] = None
    published_at: datetime
    source_provider: str


class DeadLetterEntry(BaseModel):
    """Raw payload that failed normalization."""
    provider_id: str
    raw_payload: dict
    error_message: str
    error_type: str  # 'MISSING_FIELD', 'TYPE_COERCION', 'TIMEZONE_ERROR'
    received_at: datetime = Field(default_factory=lambda: datetime.now())
