"""Researcher Agent Service — consumes market/news events, generates trade theses.

Sprint-55: Orchestrates the research pipeline:
  event consumption -> significance filter -> RAG query -> LLM call -> thesis parsing -> event emission

Includes a Significance Filter to control LLM costs (no thesis for every 1m bar).
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from karsa.thesis.ai.domain.models import (
    TradeThesis,
    ThesisSide,
    TimeHorizon,
    ConvictionScore,
    RiskFlag,
)
from karsa.thesis.ai.domain.events import ThesisGeneratedEvent
from karsa.thesis.ai.application.thesis_parser import ThesisParser

logger = logging.getLogger(__name__)


# --- Significance Filter ---

class SignificanceFilter:
    """Deterministic filter to avoid triggering LLM calls on every bar.

    Only triggers thesis generation when:
    (a) price moves >2% from previous close
    (b) a correlated news event arrives
    (c) a scheduled rebalance window opens
    """

    def __init__(
        self,
        price_move_threshold: float = 0.02,  # 2%
        rebalance_hours: Optional[List[int]] = None,  # UTC hours for scheduled rebalance
    ):
        self._threshold = price_move_threshold
        self._rebalance_hours = rebalance_hours or [9, 16]  # Market open/close UTC
        self._previous_closes: Dict[str, float] = {}  # ticker -> last close
        self._filtered_count = 0
        self._passed_count = 0

    def should_generate_thesis(
        self,
        ticker: str,
        current_price: float,
        has_correlated_news: bool = False,
        current_hour_utc: Optional[int] = None,
    ) -> bool:
        """Check if a thesis should be generated for this event.

        Args:
            ticker: Stock ticker symbol.
            current_price: Current bar close price.
            has_correlated_news: Whether a news event arrived for this ticker.
            current_hour_utc: Current hour in UTC (for rebalance check).

        Returns:
            True if thesis generation should proceed.
        """
        # Pass-through if correlated news
        if has_correlated_news:
            self._passed_count += 1
            return True

        # Check scheduled rebalance window
        hour = current_hour_utc
        if hour is not None and hour in self._rebalance_hours:
            self._passed_count += 1
            return True

        # Check price move threshold
        prev_close = self._previous_closes.get(ticker)
        if prev_close is not None and prev_close > 0:
            move_pct = abs(current_price - prev_close) / prev_close
            if move_pct >= self._threshold:
                self._passed_count += 1
                return True

        # Update previous close for next check
        self._previous_closes[ticker] = current_price
        self._filtered_count += 1
        return False

    @property
    def filtered_count(self) -> int:
        return self._filtered_count

    @property
    def passed_count(self) -> int:
        return self._passed_count


# --- Researcher Agent ---

RESEARCHER_SYSTEM_PROMPT = """You are a quantitative trade thesis generator for an autonomous trading firm.

Given market data and institutional memory context, generate a structured trade thesis.

You MUST respond with valid JSON in this exact format:
{
    "title": "Brief thesis title",
    "ticker": "STOCK_SYMBOL",
    "side": "BUY" or "SELL",
    "conviction": 0.0 to 1.0,
    "time_horizon": "INTRADAY" | "SWING" | "POSITION" | "LONG_TERM",
    "stop_loss": price or null,
    "take_profit": price or null,
    "position_size_pct": 0.0 to 5.0,
    "reasoning": "Detailed reasoning with evidence from context"
}

Rules:
- Only recommend trades with clear edge supported by institutional memory
- Conviction < 0.3 means do not trade — use "side": "HOLD" instead
- Stop loss and take profit must be mathematically sound
- Position size must not exceed 5% of portfolio
- Reference specific historical precedents from the RAG context
- If no clear edge exists, return {"side": "HOLD", "conviction": 0.0}
"""


class ResearcherAgentService:
    """Orchestrates the research pipeline: event -> filter -> RAG -> LLM -> thesis.

    Consumes market bar and news events, applies significance filter,
    queries RAG for institutional memory, and generates trade theses.
    """

    def __init__(
        self,
        call_llm: Callable,  # async callable: (group, messages, response_format) -> dict
        retrieve_context: Callable,  # async callable: (ticker, sector, query_text) -> str
        significance_filter: Optional[SignificanceFilter] = None,
        publish_event: Optional[Callable] = None,  # async callable: (event) -> None
    ):
        self._call_llm = call_llm
        self._retrieve_context = retrieve_context
        self._filter = significance_filter or SignificanceFilter()
        self._publish_event = publish_event
        self._parser = ThesisParser()
        self._thesis_count = 0

    async def on_market_bar(
        self,
        ticker: str,
        close_price: float,
        volume: int = 0,
        bar_timestamp: Optional[datetime] = None,
        sector: Optional[str] = None,
    ) -> Optional[TradeThesis]:
        """Process a market bar event.

        Applies significance filter, queries RAG, generates thesis if significant.
        """
        # Check significance
        current_hour = bar_timestamp.hour if bar_timestamp else None
        if not self._filter.should_generate_thesis(
            ticker=ticker,
            current_price=close_price,
            current_hour_utc=current_hour,
        ):
            return None

        return await self._generate_thesis(
            ticker=ticker,
            current_price=close_price,
            sector=sector,
            trigger="market_bar",
            source_event_id=None,
        )

    async def on_news_event(
        self,
        ticker: str,
        headline: str,
        sector: Optional[str] = None,
        sentiment_score: Optional[float] = None,
        article_id: Optional[str] = None,
    ) -> Optional[TradeThesis]:
        """Process a news event.

        News always passes the significance filter.
        """
        return await self._generate_thesis(
            ticker=ticker,
            current_price=0.0,  # Will be enriched from RAG context
            sector=sector,
            trigger="news",
            source_news_event_id=article_id,
            news_headline=headline,
        )

    async def _generate_thesis(
        self,
        ticker: str,
        current_price: float,
        sector: Optional[str] = None,
        trigger: str = "market_bar",
        source_event_id: Optional[str] = None,
        source_news_event_id: Optional[str] = None,
        news_headline: Optional[str] = None,
    ) -> Optional[TradeThesis]:
        """Core thesis generation pipeline."""
        # 1. Query RAG for institutional memory
        rag_context = ""
        rag_used = False
        try:
            query_text = news_headline or f"Recent price action and thesis history for {ticker}"
            rag_context = await self._retrieve_context(
                ticker=ticker,
                sector=sector,
                query_text=query_text,
            )
            rag_used = bool(rag_context)
        except Exception as e:
            logger.warning(f"RAG query failed for {ticker}, proceeding without context: {e}")

        # 2. Construct prompt
        user_prompt = f"Ticker: {ticker}\n"
        if current_price > 0:
            user_prompt += f"Current Price: {current_price}\n"
        if sector:
            user_prompt += f"Sector: {sector}\n"
        if news_headline:
            user_prompt += f"Breaking News: {news_headline}\n"
        user_prompt += f"Trigger: {trigger}\n"
        if rag_context:
            user_prompt += f"\n{rag_context}\n"

        # 3. Call LLM
        try:
            result = await self._call_llm(
                model_group="karsa-reasoning",
                messages=[
                    {"role": "system", "content": RESEARCHER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            llm_output = result.get("content", "")
        except Exception as e:
            logger.error(f"LLM call failed for {ticker}: {e}")
            return None

        # 4. Parse thesis
        thesis = self._parser.parse(
            llm_output=llm_output,
            ticker=ticker,
            source_market_event_id=source_event_id,
            source_news_event_id=source_news_event_id,
            rag_context_used=rag_used,
        )

        if thesis is None:
            logger.warning(f"Failed to parse thesis for {ticker}")
            return None

        # 5. Emit event
        if self._publish_event and thesis.side != ThesisSide.BUY or thesis.conviction.value >= 0.3:
            # Only emit if conviction is meaningful (not HOLD)
            event = ThesisGeneratedEvent(
                thesis_id=thesis.thesis_id,
                ticker=thesis.ticker,
                side=thesis.side.value,
                conviction=thesis.conviction.value,
                time_horizon=thesis.time_horizon.value,
                stop_loss=thesis.stop_loss,
                take_profit=thesis.take_profit,
                position_size_pct=thesis.position_size_pct,
                title=thesis.title,
                reasoning=thesis.reasoning,
                source_market_event_id=thesis.source_market_event_id,
                source_news_event_id=thesis.source_news_event_id,
                rag_context_used=thesis.rag_context_used,
            )
            try:
                await self._publish_event(event)
            except Exception as e:
                logger.error(f"Failed to publish ThesisGeneratedEvent: {e}")

        self._thesis_count += 1
        logger.info(
            f"Thesis generated: {thesis.ticker} {thesis.side.value} "
            f"conviction={thesis.conviction.value:.2f} "
            f"(total: {self._thesis_count})"
        )
        return thesis

    @property
    def thesis_count(self) -> int:
        return self._thesis_count

    @property
    def significance_filter(self) -> SignificanceFilter:
        return self._filter
