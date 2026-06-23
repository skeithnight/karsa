"""Unit tests for Sprint-52: Connectors, Normalization & Aggregation.

Tests cover:
- Normalization models (Pydantic validation)
- Aggregation Engine (tick buffering, OHLCV computation, window management)
- Connector registration (Polygon, Finnhub)
- Event Emitter routing
"""
import asyncio
from datetime import datetime, timezone, timedelta
import pytest

from karsa.providers.domain.normalization import (
    NormalizedMarketTick,
    NormalizedAggregatedBar,
    NormalizedNewsEvent,
    EventType,
)
from karsa.providers.application.aggregation_engine import AggregationEngine, TickBuffer
from karsa.providers.application.connector_factory import ConnectorFactory, CONNECTOR_REGISTRY
from karsa.providers.application.event_emitter import DataBridgeEventEmitter

# Ensure connectors are registered
import karsa.providers.infrastructure.connectors


# ============================================================
# Normalization Model Tests
# ============================================================

class TestNormalizationModels:
    def test_market_tick_creation(self):
        tick = NormalizedMarketTick(
            symbol="AAPL",
            price=195.50,
            volume=100,
            timestamp_utc=datetime(2026, 6, 22, 14, 30, tzinfo=timezone.utc),
            source_provider="polygon",
        )
        assert tick.event_type == EventType.MARKET_TICK
        assert tick.symbol == "AAPL"
        assert tick.price == 195.50
        assert tick.volume == 100

    def test_market_tick_frozen(self):
        tick = NormalizedMarketTick(
            symbol="AAPL", price=195.50, volume=100,
            timestamp_utc=datetime.now(timezone.utc), source_provider="polygon",
        )
        with pytest.raises(Exception):
            tick.symbol = "TSLA"

    def test_aggregated_bar_creation(self):
        bar = NormalizedAggregatedBar(
            symbol="AAPL",
            timeframe="1m",
            open=195.0,
            high=196.0,
            low=194.5,
            close=195.5,
            volume=5000,
            bar_close_utc=datetime(2026, 6, 22, 14, 31, tzinfo=timezone.utc),
            source_provider="aggregation_engine",
        )
        assert bar.event_type == EventType.MARKET_BAR
        assert bar.high > bar.low

    def test_news_event_creation(self):
        news = NormalizedNewsEvent(
            headline="Apple reports record earnings",
            url="https://example.com/news",
            tickers=["AAPL"],
            sentiment_score=0.85,
            published_at=datetime.now(timezone.utc),
            source_provider="finnhub",
        )
        assert news.event_type == EventType.NEWS_ARTICLE
        assert len(news.tickers) == 1

    def test_news_event_no_sentiment(self):
        news = NormalizedNewsEvent(
            headline="Breaking news",
            url="https://example.com",
            tickers=[],
            published_at=datetime.now(timezone.utc),
            source_provider="finnhub",
        )
        assert news.sentiment_score is None

    def test_market_tick_json_serialization(self):
        tick = NormalizedMarketTick(
            symbol="SPY", price=500.0, volume=1000,
            timestamp_utc=datetime(2026, 6, 22, 14, 0, tzinfo=timezone.utc),
            source_provider="polygon",
        )
        data = tick.model_dump(mode="json")
        assert data["symbol"] == "SPY"
        assert data["event_type"] == "MARKET_TICK"
        assert "timestamp_utc" in data


# ============================================================
# Aggregation Engine Tests
# ============================================================

class TestAggregationEngine:
    def _make_engine(self):
        bars = []

        async def capture_bar(bar):
            bars.append(bar)

        eng = AggregationEngine(timeframes=["1m"])
        eng.set_on_bar(capture_bar)
        return eng, bars

    def test_single_tick_no_bar(self):
        async def run():
            eng, bars = self._make_engine()
            tick = NormalizedMarketTick(
                symbol="AAPL", price=195.0, volume=100,
                timestamp_utc=datetime(2026, 6, 22, 14, 30, 5, tzinfo=timezone.utc),
                source_provider="polygon",
            )
            await eng.process_tick(tick)
            assert len(bars) == 0
        asyncio.run(run())

    def test_window_close_emits_bar(self):
        async def run():
            eng, bars = self._make_engine()
            base = datetime(2026, 6, 22, 14, 30, 0, tzinfo=timezone.utc)

            for i, price in enumerate([195.0, 196.0, 194.5, 195.5]):
                tick = NormalizedMarketTick(
                    symbol="AAPL", price=price, volume=100,
                    timestamp_utc=base + timedelta(seconds=i * 10),
                    source_provider="polygon",
                )
                await eng.process_tick(tick)

            next_window_tick = NormalizedMarketTick(
                symbol="AAPL", price=196.0, volume=200,
                timestamp_utc=base + timedelta(minutes=1, seconds=5),
                source_provider="polygon",
            )
            await eng.process_tick(next_window_tick)

            assert len(bars) == 1
            bar = bars[0]
            assert bar.open == 195.0
            assert bar.high == 196.0
            assert bar.low == 194.5
            assert bar.close == 195.5
            assert bar.volume == 400
            assert bar.timeframe == "1m"
            assert bar.symbol == "AAPL"
        asyncio.run(run())

    def test_flush_emits_pending_bars(self):
        async def run():
            eng, bars = self._make_engine()
            tick = NormalizedMarketTick(
                symbol="SPY", price=500.0, volume=1000,
                timestamp_utc=datetime(2026, 6, 22, 14, 30, 0, tzinfo=timezone.utc),
                source_provider="polygon",
            )
            await eng.process_tick(tick)
            assert len(bars) == 0

            await eng.flush_all()
            assert len(bars) == 1
            assert bars[0].symbol == "SPY"
        asyncio.run(run())

    def test_multiple_symbols(self):
        async def run():
            eng, bars = self._make_engine()
            base = datetime(2026, 6, 22, 14, 30, 0, tzinfo=timezone.utc)

            await eng.process_tick(NormalizedMarketTick(
                symbol="AAPL", price=195.0, volume=100,
                timestamp_utc=base, source_provider="polygon",
            ))
            await eng.process_tick(NormalizedMarketTick(
                symbol="SPY", price=500.0, volume=1000,
                timestamp_utc=base, source_provider="polygon",
            ))

            next_base = base + timedelta(minutes=1)
            await eng.process_tick(NormalizedMarketTick(
                symbol="AAPL", price=196.0, volume=100,
                timestamp_utc=next_base, source_provider="polygon",
            ))
            await eng.process_tick(NormalizedMarketTick(
                symbol="SPY", price=501.0, volume=1000,
                timestamp_utc=next_base, source_provider="polygon",
            ))

            assert len(bars) == 2
            symbols = {b.symbol for b in bars}
            assert symbols == {"AAPL", "SPY"}
        asyncio.run(run())

    def test_gap_fill(self):
        async def run():
            eng, bars = self._make_engine()
            gap_bars = [
                NormalizedAggregatedBar(
                    symbol="AAPL", timeframe="1m",
                    open=194.0, high=195.0, low=193.5, close=194.5,
                    volume=3000,
                    bar_close_utc=datetime(2026, 6, 22, 14, 28, 0, tzinfo=timezone.utc),
                    source_provider="polygon",
                ),
                NormalizedAggregatedBar(
                    symbol="AAPL", timeframe="1m",
                    open=194.5, high=195.5, low=194.0, close=195.0,
                    volume=2500,
                    bar_close_utc=datetime(2026, 6, 22, 14, 29, 0, tzinfo=timezone.utc),
                    source_provider="polygon",
                ),
            ]
            await eng.fill_gap("AAPL", "1m", gap_bars)
            assert len(bars) == 2
            assert eng.bar_count == 2
        asyncio.run(run())

    def test_window_start_1m(self):
        eng = AggregationEngine()
        ts = datetime(2026, 6, 22, 14, 30, 45, tzinfo=timezone.utc)
        result = eng._get_window_start(ts, "1m")
        assert result == datetime(2026, 6, 22, 14, 30, 0, tzinfo=timezone.utc)

    def test_window_start_5m(self):
        eng = AggregationEngine()
        ts = datetime(2026, 6, 22, 14, 33, 0, tzinfo=timezone.utc)
        result = eng._get_window_start(ts, "5m")
        assert result == datetime(2026, 6, 22, 14, 30, 0, tzinfo=timezone.utc)

    def test_window_start_1h(self):
        eng = AggregationEngine()
        ts = datetime(2026, 6, 22, 14, 45, 0, tzinfo=timezone.utc)
        result = eng._get_window_start(ts, "1h")
        assert result == datetime(2026, 6, 22, 14, 0, 0, tzinfo=timezone.utc)


# ============================================================
# TickBuffer Tests
# ============================================================

class TestTickBuffer:
    def test_empty_buffer_returns_none(self):
        buf = TickBuffer("AAPL", "1m", datetime.now(timezone.utc))
        assert buf.compute_bar("test") is None

    def test_compute_bar_single_tick(self):
        window = datetime(2026, 6, 22, 14, 30, 0, tzinfo=timezone.utc)
        buf = TickBuffer("AAPL", "1m", window)
        buf.add_tick(NormalizedMarketTick(
            symbol="AAPL", price=195.0, volume=100,
            timestamp_utc=window, source_provider="test",
        ))
        bar = buf.compute_bar("test")
        assert bar.open == 195.0
        assert bar.high == 195.0
        assert bar.low == 195.0
        assert bar.close == 195.0
        assert bar.volume == 100

    def test_compute_bar_multiple_ticks(self):
        window = datetime(2026, 6, 22, 14, 30, 0, tzinfo=timezone.utc)
        buf = TickBuffer("AAPL", "1m", window)
        for price in [195.0, 197.0, 193.0, 196.0]:
            buf.add_tick(NormalizedMarketTick(
                symbol="AAPL", price=price, volume=100,
                timestamp_utc=window, source_provider="test",
            ))
        bar = buf.compute_bar("test")
        assert bar.open == 195.0
        assert bar.high == 197.0
        assert bar.low == 193.0
        assert bar.close == 196.0
        assert bar.volume == 400


# ============================================================
# Connector Registration Tests
# ============================================================

class TestConnectorRegistration:
    def test_polygon_registered(self):
        assert "polygon" in CONNECTOR_REGISTRY

    def test_finnhub_registered(self):
        assert "finnhub" in CONNECTOR_REGISTRY

    def test_create_polygon_connector(self):
        connector = ConnectorFactory.create(
            provider_name="polygon",
            provider_id="p1",
            config={"symbols": ["AAPL"]},
            credentials={"api_key": "test-key"},
        )
        assert connector.provider_id == "p1"
        assert connector.config == {"symbols": ["AAPL"]}

    def test_create_finnhub_connector(self):
        connector = ConnectorFactory.create(
            provider_name="finnhub",
            provider_id="p2",
            config={"category": "general"},
            credentials={"api_key": "test-key"},
        )
        assert connector.provider_id == "p2"


# ============================================================
# Event Emitter Tests
# ============================================================

class TestEventEmitter:
    def test_emitter_tracks_count(self):
        mock_bus = type("MockBus", (), {"publish": lambda self, e: None})()
        emitter = DataBridgeEventEmitter(mock_bus)
        assert emitter.emit_count == 0
