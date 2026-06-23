"""Red Team Test Suite — Sprint-55 adversarial validation.

10+ test cases covering hallucination detection, logical inconsistency,
risk limit enforcement, and valid thesis scenarios. Designed to verify
the Governance Agent correctly rejects dangerous theses and approves
sound ones.
"""
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
from karsa.thesis.ai.application.governance_agent import GovernanceAgentService
from karsa.thesis.ai.application.thesis_parser import ThesisParser
from karsa.thesis.ai.application.researcher_agent import SignificanceFilter


class TestRedTeamHallucination:
    """Test cases for hallucination detection."""

    def _make_agent(self, llm_decision):
        mock_llm = AsyncMock(return_value={
            "content": json.dumps(llm_decision),
            "model": "gpt-4o-mini",
        })
        mock_rag = AsyncMock(return_value="No acquisition news found for AAPL or MSFT")
        mock_publish = AsyncMock()
        return GovernanceAgentService(
            call_llm=mock_llm,
            retrieve_context=mock_rag,
            publish_event=mock_publish,
        ), mock_publish

    def test_01_apple_acquires_microsoft_rejected(self):
        """Hallucinated acquisition claim must be rejected."""
        thesis = TradeThesis(
            ticker="AAPL",
            side=ThesisSide.BUY,
            conviction=ConvictionScore(0.95),
            title="Apple acquires Microsoft for $3T",
            reasoning="Apple announced acquisition of Microsoft, expecting massive synergies",
        )
        agent, mock_pub = self._make_agent({
            "approved": False,
            "reasoning": "No credible source confirms Apple-Microsoft acquisition. This is a hallucination.",
            "risk_flags": ["HALLUCINATION"],
        })
        async def run():
            decision = await agent.validate_thesis(thesis)
            assert decision.approved is False
            assert RiskFlag.HALLUCINATION in decision.risk_flags
            # Must emit rejection event
            mock_pub.assert_called_once()
            event = mock_pub.call_args[0][0]
            assert "HALLUCINATION" in event.risk_flags
        asyncio.run(run())

    def test_02_tesla_bankruptcy_hallucination(self):
        """False bankruptcy claim must be rejected."""
        thesis = TradeThesis(
            ticker="TSLA",
            side=ThesisSide.SELL,
            conviction=ConvictionScore(0.9),
            title="Tesla files for Chapter 11",
            reasoning="Tesla has filed for bankruptcy protection",
        )
        agent, _ = self._make_agent({
            "approved": False,
            "reasoning": "Tesla has not filed for bankruptcy. Claim is unsubstantiated.",
            "risk_flags": ["HALLUCINATION"],
        })
        async def run():
            decision = await agent.validate_thesis(thesis)
            assert decision.approved is False
            assert RiskFlag.HALLUCINATION in decision.risk_flags
        asyncio.run(run())


class TestRedTeamLogicalConsistency:
    """Test cases for logical inconsistency detection."""

    def _make_agent(self, llm_decision):
        mock_llm = AsyncMock(return_value={
            "content": json.dumps(llm_decision),
            "model": "gpt-4o-mini",
        })
        return GovernanceAgentService(call_llm=mock_llm), mock_llm

    def test_03_buy_with_stop_above_entry(self):
        """BUY thesis with stop-loss above entry price is logically inconsistent."""
        thesis = TradeThesis(
            ticker="AAPL",
            side=ThesisSide.BUY,
            conviction=ConvictionScore(0.7),
            stop_loss=200.0,  # Above entry — wrong direction
            title="AAPL momentum play",
            reasoning="Strong uptrend continuation expected",
        )
        agent, _ = self._make_agent({
            "approved": False,
            "reasoning": "Stop loss at 200 is above entry for a BUY. This would trigger immediately.",
            "risk_flags": ["LOGICAL_INCONSISTENCY"],
        })
        async def run():
            decision = await agent.validate_thesis(thesis)
            assert decision.approved is False
            assert RiskFlag.LOGICAL_INCONSISTENCY in decision.risk_flags
        asyncio.run(run())

    def test_04_zero_conviction_with_side(self):
        """Thesis with near-zero conviction but BUY/SELL side is inconsistent."""
        thesis = TradeThesis(
            ticker="AAPL",
            side=ThesisSide.BUY,
            conviction=ConvictionScore(0.05),
            title="Weak signal",
            reasoning="Not much evidence",
        )
        agent, _ = self._make_agent({
            "approved": False,
            "reasoning": "Conviction of 0.05 is too low for a directional trade.",
            "risk_flags": ["LOGICAL_INCONSISTENCY"],
        })
        async def run():
            decision = await agent.validate_thesis(thesis)
            assert decision.approved is False
        asyncio.run(run())

    def test_05_take_profit_below_entry_for_buy(self):
        """BUY with take-profit below entry makes no sense."""
        thesis = TradeThesis(
            ticker="AAPL",
            side=ThesisSide.BUY,
            conviction=ConvictionScore(0.7),
            stop_loss=180.0,
            take_profit=150.0,  # Below entry — wrong
            title="AAPL play",
            reasoning="test",
        )
        agent, _ = self._make_agent({
            "approved": False,
            "reasoning": "Take profit at 150 is below entry for a BUY position.",
            "risk_flags": ["LOGICAL_INCONSISTENCY"],
        })
        async def run():
            decision = await agent.validate_thesis(thesis)
            assert decision.approved is False
            assert RiskFlag.LOGICAL_INCONSISTENCY in decision.risk_flags
        asyncio.run(run())


class TestRedTeamRiskLimits:
    """Test cases for risk limit enforcement."""

    def _make_agent(self, llm_decision):
        mock_llm = AsyncMock(return_value={
            "content": json.dumps(llm_decision),
            "model": "gpt-4o-mini",
        })
        return GovernanceAgentService(call_llm=mock_llm), mock_llm

    def test_06_position_size_exceeded_rejected_without_llm(self):
        """Position size >5% must be rejected by deterministic check, no LLM call."""
        thesis = TradeThesis(
            ticker="AAPL",
            side=ThesisSide.BUY,
            conviction=ConvictionScore(0.8),
            position_size_pct=15.0,  # Way over 5%
            title="Big bet",
            reasoning="test",
        )
        agent, mock_llm = self._make_agent({
            "approved": True,  # LLM would approve — but deterministic check overrides
            "reasoning": "Looks good",
            "risk_flags": [],
        })
        async def run():
            decision = await agent.validate_thesis(thesis)
            assert decision.approved is False
            assert RiskFlag.POSITION_SIZE_EXCEEDED in decision.risk_flags
            # LLM should NOT have been called (deterministic rejection)
            mock_llm.assert_not_called()
        asyncio.run(run())

    def test_07_adjusted_position_size_on_approval(self):
        """Governance can adjust position size down on approval."""
        thesis = TradeThesis(
            ticker="AAPL",
            side=ThesisSide.BUY,
            conviction=ConvictionScore(0.7),
            position_size_pct=3.0,
            title="Reasonable trade",
            reasoning="Solid setup",
        )
        agent, _ = self._make_agent({
            "approved": True,
            "reasoning": "Approved but reduce size due to volatility",
            "risk_flags": [],
            "adjusted_position_size_pct": 1.5,
        })
        async def run():
            decision = await agent.validate_thesis(thesis)
            assert decision.approved is True
            assert decision.adjusted_position_size_pct == 1.5
        asyncio.run(run())


class TestRedTeamValidScenarios:
    """Test cases for valid thesis approval."""

    def _make_agent(self, llm_decision):
        mock_llm = AsyncMock(return_value={
            "content": json.dumps(llm_decision),
            "model": "gpt-4o-mini",
        })
        mock_rag = AsyncMock(return_value="AAPL broke out of similar pattern in Jan 2025, +8% in 5 days")
        mock_publish = AsyncMock()
        return GovernanceAgentService(
            call_llm=mock_llm,
            retrieve_context=mock_rag,
            publish_event=mock_publish,
        ), mock_publish

    def test_08_valid_thesis_approved(self):
        """Sound thesis with RAG support should be approved."""
        thesis = TradeThesis(
            ticker="AAPL",
            side=ThesisSide.BUY,
            conviction=ConvictionScore(0.75),
            time_horizon=TimeHorizon.SWING,
            stop_loss=190.0,
            take_profit=210.0,
            position_size_pct=2.0,
            title="AAPL breakout with volume confirmation",
            reasoning="Strong volume breakout above 200-day SMA, RAG shows similar pattern yielded +8%",
        )
        agent, mock_pub = self._make_agent({
            "approved": True,
            "reasoning": "Strong technical setup confirmed by institutional memory. R/R ratio is 2:1.",
            "risk_flags": [],
        })
        async def run():
            decision = await agent.validate_thesis(thesis)
            assert decision.approved is True
            assert len(decision.risk_flags) == 0
            # Must emit approval event
            mock_pub.assert_called_once()
            event = mock_pub.call_args[0][0]
            assert event.ticker == "AAPL"
        asyncio.run(run())

    def test_09_valid_sell_thesis_approved(self):
        """Valid SELL thesis should also be approved."""
        thesis = TradeThesis(
            ticker="NVDA",
            side=ThesisSide.SELL,
            conviction=ConvictionScore(0.65),
            time_horizon=TimeHorizon.POSITION,
            stop_loss=150.0,
            take_profit=100.0,
            position_size_pct=1.5,
            title="NVDA overextended, mean reversion expected",
            reasoning="RSI > 80, 3 standard deviations above mean, post-earnings fade",
        )
        agent, _ = self._make_agent({
            "approved": True,
            "reasoning": "Overextension confirmed by multiple indicators. Risk-managed position.",
            "risk_flags": [],
        })
        async def run():
            decision = await agent.validate_thesis(thesis)
            assert decision.approved is True
        asyncio.run(run())


class TestRedTeamFailureModes:
    """Test cases for failure mode handling."""

    def test_10_governance_llm_timeout_fails_closed(self):
        """If governance LLM times out, thesis must be rejected (fail-closed)."""
        mock_llm = AsyncMock(side_effect=TimeoutError("LLM request timed out"))
        agent = GovernanceAgentService(call_llm=mock_llm)
        thesis = TradeThesis(
            ticker="AAPL",
            side=ThesisSide.BUY,
            conviction=ConvictionScore(0.8),
            title="Test",
            reasoning="test",
        )
        async def run():
            decision = await agent.validate_thesis(thesis)
            assert decision.approved is False
            assert RiskFlag.PARSE_FAILURE in decision.risk_flags
        asyncio.run(run())

    def test_11_parser_handles_malformed_json(self):
        """Parser must handle malformed LLM output gracefully."""
        parser = ThesisParser()
        # Partial JSON
        assert parser.parse('{"title": "test", "ticker":') is None
        # Empty string
        assert parser.parse("") is None
        # Markdown with no JSON
        assert parser.parse("I think AAPL is a buy because...") is None
        # JSON with wrong types
        result = parser.parse('{"title": 123, "side": "INVALID"}')
        assert result is not None  # Should coerce defaults

    def test_12_significance_filter_baseline_none(self):
        """Filter must not trigger on first bar (no baseline)."""
        f = SignificanceFilter(price_move_threshold=0.02)
        # First bar — no previous close
        assert f.should_generate_thesis("AAPL", 150.0) is False
        # Second bar — now has baseline
        assert f.should_generate_thesis("AAPL", 153.0) is True  # 2% move

    def test_13_governance_rejects_on_rag_failure(self):
        """Governance should still work (but be more skeptical) when RAG fails."""
        mock_llm = AsyncMock(return_value={
            "content": json.dumps({
                "approved": False,
                "reasoning": "Cannot verify claims without institutional memory. Rejecting conservatively.",
                "risk_flags": ["NO_RAG_CONTEXT"],
            }),
            "model": "gpt-4o-mini",
        })
        mock_rag = AsyncMock(side_effect=Exception("pgvector down"))
        agent = GovernanceAgentService(call_llm=mock_llm, retrieve_context=mock_rag)
        thesis = TradeThesis(ticker="AAPL", title="test", reasoning="test")
        async def run():
            decision = await agent.validate_thesis(thesis)
            assert decision.approved is False
        asyncio.run(run())
