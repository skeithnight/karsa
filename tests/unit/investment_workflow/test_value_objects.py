"""Tests for Investment Workflow value objects -- Sprint-13. ADR-140.

Covers:
- ConvictionScore validation and computation
- AnalystScore validation
- DecisionMemo validation
- Enum correctness
"""

import pytest
from decimal import Decimal

from karsa.investment_workflow.domain.exceptions import InvalidMemoError
from karsa.investment_workflow.domain.value_objects.conviction_score import (
    ConvictionScore,
)
from karsa.investment_workflow.domain.value_objects.analyst_score import AnalystScore
from karsa.investment_workflow.domain.value_objects.decision_memo import DecisionMemo
from karsa.investment_workflow.domain.value_objects.enums import (
    AnalystType,
    ConvictionLevel,
    DecisionState,
    DecisionType,
    VALID_TRANSITIONS,
)


class TestConvictionScore:
    """ConvictionScore value object."""

    def test_valid_score(self):
        cs = ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3)
        assert cs.level == "STRONG"
        assert cs.numeric_score == 8.0

    def test_frozen(self):
        cs = ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3)
        with pytest.raises(AttributeError):
            cs.level = "WEAK"

    def test_invalid_score_range(self):
        with pytest.raises(ValueError, match="numeric_score"):
            ConvictionScore(level="STRONG", numeric_score=11.0, analyst_agreement=3)

    def test_invalid_agreement_range(self):
        with pytest.raises(ValueError, match="analyst_agreement"):
            ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=6)

    def test_invalid_level(self):
        with pytest.raises(ValueError, match="level"):
            ConvictionScore(level="INVALID", numeric_score=8.0, analyst_agreement=3)

    def test_from_analyst_scores_strong(self):
        scores = [8.0, 7.0, 6.5, 5.0]
        cs = ConvictionScore.from_analyst_scores(scores)
        assert cs.level == "STRONG"
        assert cs.analyst_agreement == 3

    def test_from_analyst_scores_medium(self):
        scores = [7.0, 6.5, 4.0, 3.0]
        cs = ConvictionScore.from_analyst_scores(scores)
        assert cs.level == "MEDIUM"
        assert cs.analyst_agreement == 2

    def test_from_analyst_scores_weak(self):
        scores = [7.0, 4.0, 3.0, 2.0]
        cs = ConvictionScore.from_analyst_scores(scores)
        assert cs.level == "WEAK"
        assert cs.analyst_agreement == 1


class TestAnalystScore:
    """AnalystScore value object."""

    def test_valid_score(self):
        a = AnalystScore(analyst_type="FUNDAMENTAL", score=7.5, confidence=0.8)
        assert a.analyst_type == "FUNDAMENTAL"

    def test_frozen(self):
        a = AnalystScore(analyst_type="FUNDAMENTAL", score=7.5, confidence=0.8)
        with pytest.raises(AttributeError):
            a.score = 9.0

    def test_invalid_type(self):
        with pytest.raises(ValueError, match="analyst_type"):
            AnalystScore(analyst_type="INVALID", score=7.5, confidence=0.8)

    def test_invalid_score(self):
        with pytest.raises(ValueError, match="score"):
            AnalystScore(analyst_type="FUNDAMENTAL", score=11.0, confidence=0.8)

    def test_invalid_confidence(self):
        with pytest.raises(ValueError, match="confidence"):
            AnalystScore(analyst_type="FUNDAMENTAL", score=7.5, confidence=1.5)

    def test_with_metrics(self):
        a = AnalystScore(
            analyst_type="FUNDAMENTAL",
            score=7.5,
            confidence=0.8,
            metrics={"pe_ratio": 15.8, "dividend_yield": 3.5},
        )
        assert a.metrics["pe_ratio"] == 15.8


class TestDecisionMemo:
    """DecisionMemo value object."""

    def test_valid_memo(self):
        m = DecisionMemo(
            ticker="BBCA",
            decision="BUY",
            conviction=ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3),
            thesis="BBCA offers strong dividend yield and growth potential with reasonable valuation entry point",
        )
        assert m.ticker == "BBCA"
        assert m.decision == "BUY"

    def test_frozen(self):
        m = DecisionMemo(
            ticker="BBCA",
            decision="BUY",
            conviction=ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3),
            thesis="BBCA offers strong dividend yield and growth potential with reasonable valuation entry point",
        )
        with pytest.raises(AttributeError):
            m.ticker = "ASII"

    def test_empty_ticker(self):
        with pytest.raises(InvalidMemoError, match="ticker"):
            DecisionMemo(
                ticker="",
                decision="BUY",
                conviction=ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3),
                thesis="BBCA offers strong dividend yield and growth potential with reasonable valuation entry point",
            )

    def test_invalid_decision(self):
        with pytest.raises(InvalidMemoError, match="decision"):
            DecisionMemo(
                ticker="BBCA",
                decision="INVALID",
                conviction=ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3),
                thesis="BBCA offers strong dividend yield and growth potential with reasonable valuation entry point",
            )

    def test_thesis_too_short(self):
        with pytest.raises(InvalidMemoError, match="thesis"):
            DecisionMemo(
                ticker="BBCA",
                decision="BUY",
                conviction=ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3),
                thesis="Too short",
            )

    def test_position_size_out_of_range(self):
        with pytest.raises(InvalidMemoError, match="position_size_pct"):
            DecisionMemo(
                ticker="BBCA",
                decision="BUY",
                conviction=ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3),
                thesis="BBCA offers strong dividend yield and growth potential with reasonable valuation entry point",
                position_size_pct=150.0,
            )

    def test_with_optional_fields(self):
        m = DecisionMemo(
            ticker="BBCA",
            decision="BUY",
            conviction=ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3),
            thesis="BBCA offers strong dividend yield and growth potential with reasonable valuation entry point",
            entry_price=Decimal("8500"),
            exit_target=Decimal("9200"),
            stop_loss=Decimal("8200"),
            position_size_pct=2.5,
        )
        assert m.entry_price == Decimal("8500")
        assert m.exit_target == Decimal("9200")


class TestEnums:
    """Enum correctness."""

    def test_decision_states(self):
        assert len(DecisionState) == 10
        assert DecisionState.PROPOSED.value == "PROPOSED"
        assert DecisionState.APPROVED.value == "APPROVED"

    def test_analyst_types(self):
        assert len(AnalystType) == 5
        assert AnalystType.FUNDAMENTAL.value == "FUNDAMENTAL"

    def test_conviction_levels(self):
        assert len(ConvictionLevel) == 3
        assert ConvictionLevel.STRONG.value == "STRONG"

    def test_decision_types(self):
        assert len(DecisionType) == 4
        assert DecisionType.BUY.value == "BUY"

    def test_valid_transitions_complete(self):
        """All non-terminal states must have transitions defined."""
        non_terminal = {s for s in DecisionState if s not in {
            DecisionState.APPROVED, DecisionState.REJECTED
        }}
        for state in non_terminal:
            assert state in VALID_TRANSITIONS
            assert len(VALID_TRANSITIONS[state]) > 0

    def test_terminal_states_have_no_transitions(self):
        assert VALID_TRANSITIONS[DecisionState.APPROVED] == set()
        assert VALID_TRANSITIONS[DecisionState.REJECTED] == set()
