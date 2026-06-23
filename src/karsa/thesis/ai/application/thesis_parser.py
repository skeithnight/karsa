"""Thesis Parser — extracts structured TradeThesis from LLM JSON output.

Sprint-55: Handles parsing, validation, and fallback for unparseable LLM responses.
"""
import json
import logging
from typing import Any, Dict, Optional

from karsa.thesis.ai.domain.models import (
    TradeThesis,
    ThesisSide,
    TimeHorizon,
    ConvictionScore,
    RiskFlag,
)

logger = logging.getLogger(__name__)


class ThesisParser:
    """Parses LLM JSON output into a structured TradeThesis.

    Handles malformed JSON, missing fields, and type coercion.
    Returns None if the output is completely unparseable.
    """

    def parse(
        self,
        llm_output: str,
        ticker: str = "",
        source_market_event_id: Optional[str] = None,
        source_news_event_id: Optional[str] = None,
        rag_context_used: bool = False,
    ) -> Optional[TradeThesis]:
        """Parse LLM output into a TradeThesis.

        Args:
            llm_output: Raw LLM response (expected JSON string).
            ticker: Ticker symbol (fallback if not in LLM output).
            source_market_event_id: ID of the triggering market event.
            source_news_event_id: ID of the triggering news event.
            rag_context_used: Whether RAG context was available.

        Returns:
            TradeThesis if parseable, None otherwise.
        """
        data = self._extract_json(llm_output)
        if data is None:
            logger.warning(f"Could not extract JSON from LLM output: {llm_output[:200]}")
            return None

        try:
            # Parse side
            side_str = data.get("side", "BUY").upper()
            try:
                side = ThesisSide(side_str)
            except ValueError:
                side = ThesisSide.BUY

            # Parse conviction
            conviction_val = float(data.get("conviction", 0.0))
            conviction = ConvictionScore(value=conviction_val)

            # Parse time horizon
            horizon_str = data.get("time_horizon", "SWING").upper()
            try:
                time_horizon = TimeHorizon(horizon_str)
            except ValueError:
                time_horizon = TimeHorizon.SWING

            # Parse numeric fields
            stop_loss = data.get("stop_loss")
            if stop_loss is not None:
                stop_loss = float(stop_loss)

            take_profit = data.get("take_profit")
            if take_profit is not None:
                take_profit = float(take_profit)

            position_size_pct = float(data.get("position_size_pct", 1.0))
            position_size_pct = max(0.0, min(5.0, position_size_pct))  # Cap at 5%

            thesis = TradeThesis(
                ticker=data.get("ticker", ticker),
                side=side,
                conviction=conviction,
                time_horizon=time_horizon,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size_pct=position_size_pct,
                title=data.get("title", ""),
                reasoning=data.get("reasoning", ""),
                source_market_event_id=source_market_event_id,
                source_news_event_id=source_news_event_id,
                rag_context_used=rag_context_used,
            )

            return thesis

        except Exception as e:
            logger.error(f"Thesis parse error: {e} | data: {data}")
            return None

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM output, handling markdown code blocks."""
        if not text:
            return None

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                # Remove language identifier (e.g., "json\n")
                if "\n" in part:
                    part = part.split("\n", 1)[1] if part.strip().startswith("json") else part
                part = part.strip()
                if part.startswith("{"):
                    try:
                        return json.loads(part)
                    except json.JSONDecodeError:
                        continue

        # Try finding first { ... } block
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        return None
