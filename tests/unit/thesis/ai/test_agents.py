"""Unit tests for Sprint-55: Researcher Agent, Governance Agent, Thesis Parser."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from karsa.thesis.ai.domain.models import (
    TradeThesis,
    ThesisSide,
    TimeHorizon,
    ConvictionScore,
    GovernanceDecision,
    RiskFlag,
)
from karsa.thesis.ai.application.thesis_parser import ThesisParser
from karsa.thesis.ai.application.researcher_agent import ResearcherAgentService, SignificanceFilter
from karsa.thesis.ai.application.governance_agent import GovernanceAgentService


# ============================================================
# Thesis Parser Tests
# ============================================================

class TestThesisParser:
    def _make_parser(self):
        return ThesisParser()

    def test_parse_valid_json(self):
        parser = self._make_parser()
        output = json.dumps({
            "title": "AAPL breakout",
            "ticker": "AAPL",
            "side": "BUY",
            "conviction": 0.75,
            "time_horizon": "SWING",
            "stop_loss": 190.0,
            "take_profit": 210.0,
            "position_size_pct": 2.0,
            "reasoning": "Strong momentum with RAG support",
        })
        thesis = parser.parse(output, ticker="AAPL")
        assert thesis is not None
        assert thesis.ticker == "AAPL"
        assert thesis.side == ThesisSide.BUY
        assert thesis.conviction.value == 0.75
        assert thesis.time_horizon == TimeHorizon.SWING

    def test_parse_markdown_code_block(self):
        parser = self._make_parser()
        output = '```json\n{"title":"Test","ticker":"TSLA","side":"SELL","conviction":0.6,"time_horizon":"INTRADAY","reasoning":"test"}\n```'
        thesis = parser.parse(output)
        assert thesis is not None
        assert thesis.ticker == "TSLA"
        assert thesis.side == ThesisSide.SELL

    def test_parse_invalid_json_returns_none(self):
        parser = self._make_parser()
        assert parser.parse("not json at all") is None
        assert parser.parse("") is None

    def test_parse_clamps_position_size(self):
        parser = self._make_parser()
        output = json.dumps({
            "title": "Test", "ticker": "X", "side": "BUY",
            "conviction": 0.5, "time_horizon": "SWING",
            "position_size_pct": 10.0, "reasoning": "test",
        })
        thesis = parser.parse(output)
        assert thesis.position_size_pct == 5.0  # Clamped to max

    def test_parse_defaults_on_missing_fields(self):
        parser = self._make_parser()
        output = json.dumps({"title": "Minimal"})
        thesis = parser.parse(output, ticker="FALLBACK")
        assert thesis is not None
        assert thesis.ticker == "FALLBACK"
        assert thesis.side == ThesisSide.BUY  # Default


# ============================================================
# Governance Agent Tests
# ============================================================

class TestGovernanceAgent:
    def _make_agent(self, llm_response=None):
        if llm_response is None:
            llm_response = {
                "content": json.dumps({
                    "approved": True,
                    "reasoning": "Thesis is sound with good RAG support.",
                    "risk_flags": [],
                }),
                "model": "gpt-4o-mini",
            }
        mock_llm = AsyncMock(return_value=llm_response)
        mock_rag = AsyncMock(return_value="RAG context for cross-reference")
        mock_publish = AsyncMock()
        return GovernanceAgentService(
            call_llm=mock_llm,
            retrieve_context=mock_rag,
            publish_event=mock_publish,
        ), mock_llm, mock_rag, mock_publish

    def test_approves_sound_thesis(self):
        thesis = TradeThesis(
            ticker="AAPL",
            side=ThesisSide.BUY,
            conviction=ConvictionScore(0.8),
            stop_loss=190.0,
            take_profit=210.0,
            position_size_pct=2.0,
            title="Strong breakout",
            reasoning="Multiple indicators align",
        )
        agent, _, _, _ = self._make_agent()
        async def run():
            decision = await agent.validate_thesis(thesis)
            assert decision.approved is True
            assert len(decision.risk_flags) == 0
        asyncio.run(run())

    def test_rejects_hallucination(self):
        llm_response = {
            "content": json.dumps({
                "approved": False,
                "reasoning": "Claims Apple acquired Microsoft — hallucination.",
                "risk_flags": ["HALLUCINATION"],
            }),
            "model": "gpt-4o-mini",
        }
        thesis = TradeThesis(
            ticker="AAPL",
            side=ThesisSide.BUY,
            conviction=ConvictionScore(0.9),
            title="Apple acquires Microsoft",
            reasoning="Apple acquired Microsoft for $1T",
        )
        agent, _, _, mock_pub = self._make_agent(llm_response)
        async def run():
            decision = await agent.validate_thesis(thesis)
            assert decision.approved is False
            assert RiskFlag.HALLUCINATION in decision.risk_flags
            mock_pub.assert_called_once()
        asyncio.run(run())

    def test_rejects_oversized_position(self):
        thesis = TradeThesis(
            ticker="AAPL",
            side=ThesisSide.BUY,
            conviction=ConvictionScore(0.8),
            position_size_pct=10.0,  # Exceeds 5% limit
            title="Big bet",
            reasoning="test",
        )
        agent, _, _, _ = self._make_agent()
        async def run():
            decision = await agent.validate_thesis(thesis)
            assert decision.approved is False
            assert RiskFlag.POSITION_SIZE_EXCEEDED in decision.risk_flags
        asyncio.run(run())

    def test_rejects_on_llm_failure(self):
        mock_llm = AsyncMock(side_effect=Exception("API down"))
        agent = GovernanceAgentService(call_llm=mock_llm)
        thesis = TradeThesis(ticker="AAPL", title="test", reasoning="test")
        async def run():
            decision = await agent.validate_thesis(thesis)
            assert decision.approved is False  # Fail-closed
            assert RiskFlag.PARSE_FAILURE in decision.risk_flags
        asyncio.run(run())


# ============================================================
# Researcher Agent Tests
# ============================================================

class TestResearcherAgent:
    def _make_agent(self, llm_content=None):
        if llm_content is None:
            llm_content = json.dumps({
                "title": "AAPL momentum",
                "ticker": "AAPL",
                "side": "BUY",
                "conviction": 0.7,
                "time_horizon": "SWING",
                "stop_loss": 190.0,
                "take_profit": 210.0,
                "position_size_pct": 2.0,
                "reasoning": "Strong momentum with RAG support",
            })
        mock_llm = AsyncMock(return_value={"content": llm_content, "model": "gpt-4o"})
        mock_rag = AsyncMock(return_value="Historical context: AAPL broke out similarly in Jan 2025")
        mock_publish = AsyncMock()
        sig_filter = SignificanceFilter(price_move_threshold=0.02)
        return ResearcherAgentService(
            call_llm=mock_llm,
            retrieve_context=mock_rag,
            significance_filter=sig_filter,
            publish_event=mock_publish,
        ), mock_llm, mock_rag, mock_publish

    def test_generates_thesis_on_significant_move(self):
        agent, mock_llm, mock_rag, mock_pub = self._make_agent()
        async def run():
            # Set baseline
            agent._filter._previous_closes["AAPL"] = 100.0
            thesis = await agent.on_market_bar(
                ticker="AAPL",
                close_price=103.0,  # 3% move
            )
            assert thesis is not None
            assert thesis.ticker == "AAPL"
            mock_llm.assert_called_once()
            mock_rag.assert_called_once()
        asyncio.run(run())

    def test_filtered_out_on_small_move(self):
        agent, mock_llm, _, _ = self._make_agent()
        async def run():
            agent._filter._previous_closes["AAPL"] = 100.0
            thesis = await agent.on_market_bar(
                ticker="AAPL",
                close_price=100.5,  # 0.5% move — below threshold
            )
            assert thesis is None
            mock_llm.assert_not_called()
        asyncio.run(run())

    def test_news_bypasses_filter(self):
        agent, mock_llm, _, _ = self._make_agent()
        async def run():
            thesis = await agent.on_news_event(
                ticker="AAPL",
                headline="Apple beats earnings by 20%",
            )
            assert thesis is not None
            mock_llm.assert_called_once()
        asyncio.run(run())

    def test_handles_llm_failure_gracefully(self):
        agent, mock_llm, _, _ = self._make_agent()
        mock_llm.side_effect = Exception("LLM down")
        async def run():
            agent._filter._previous_closes["AAPL"] = 100.0
            thesis = await agent.on_market_bar(ticker="AAPL", close_price=103.0)
            assert thesis is None  # Graceful failure
        asyncio.run(run())
