"""Tests for InvestmentDecision aggregate -- Sprint-13. ADR-140.

Covers:
- aggregate creation
- state transitions
- analyst output recording
- debate recording
- memo creation
- conviction scoring
- immutability
"""

import pytest
from datetime import datetime

from karsa.investment_workflow.domain.aggregates.investment_decision import (
    InvestmentDecision,
)
from karsa.investment_workflow.domain.entities.analyst_output import AnalystOutput
from karsa.investment_workflow.domain.entities.debate_round import DebateRound
from karsa.investment_workflow.domain.exceptions import (
    DuplicateAnalystError,
    InvalidDecisionError,
    InvalidTransitionError,
)
from karsa.investment_workflow.domain.value_objects.conviction_score import (
    ConvictionScore,
)
from karsa.investment_workflow.domain.value_objects.decision_memo import DecisionMemo
from karsa.investment_workflow.domain.value_objects.enums import (
    AnalystType,
    ConvictionLevel,
    DecisionState,
    DecisionType,
)


def _make_decision(**overrides):
    defaults = dict(
        decision_id="urn:karsa:investment:decision:test001",
        capability_family_id="family-001",
        ticker="BBCA",
        decision_date="2026-06-21",
        state=DecisionState.PROPOSED.value,
    )
    defaults.update(overrides)
    return InvestmentDecision(**defaults)


def _make_analyst_output(analyst_type="FUNDAMENTAL", score=7.5):
    return AnalystOutput(
        analyst_type=analyst_type,
        score=score,
        confidence=0.8,
        output_text=f"Analysis output for {analyst_type}",
        tools_used=["YFinance"],
        model_version="v1.0",
    )


def _make_debate():
    return DebateRound(
        round_number=1,
        bull_memo="Bull case: strong fundamentals and technicals support buy thesis at current levels",
        bear_memo="Bear case: macro headwinds and valuation concerns suggest caution at current price",
        bull_conviction=ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3),
        bear_conviction=ConvictionScore(level="WEAK", numeric_score=3.0, analyst_agreement=1),
    )


def _make_memo():
    return DecisionMemo(
        ticker="BBCA",
        decision=DecisionType.BUY.value,
        conviction=ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3),
        thesis="BBCA offers strong dividend yield and growth potential with reasonable valuation entry point",
        entry_price=8500,
        exit_target=9200,
        position_size_pct=2.5,
    )


class TestAggregateCreation:
    """InvestmentDecision aggregate creation."""

    def test_valid_decision(self):
        d = _make_decision()
        assert d.decision_id == "urn:karsa:investment:decision:test001"
        assert d.ticker == "BBCA"
        assert d.state == DecisionState.PROPOSED.value

    def test_frozen_after_init(self):
        d = _make_decision()
        with pytest.raises(AttributeError):
            d.ticker = "ASII"

    def test_missing_decision_id(self):
        with pytest.raises(InvalidDecisionError, match="decision_id"):
            _make_decision(decision_id="")

    def test_missing_ticker(self):
        with pytest.raises(InvalidDecisionError, match="ticker"):
            _make_decision(ticker="")

    def test_missing_family_id(self):
        with pytest.raises(InvalidDecisionError, match="capability_family_id"):
            _make_decision(capability_family_id="")

    def test_invalid_state(self):
        with pytest.raises(InvalidDecisionError, match="state"):
            _make_decision(state="INVALID_STATE")


class TestStateTransitions:
    """State machine transitions."""

    def test_proposed_to_analyzing(self):
        d = _make_decision()
        d.transition_to(DecisionState.ANALYZING.value)
        assert d.state == DecisionState.ANALYZING.value

    def test_analyzing_to_debating(self):
        d = _make_decision(state=DecisionState.ANALYZING.value)
        d.transition_to(DecisionState.DEBATING.value)
        assert d.state == DecisionState.DEBATING.value

    def test_debating_to_deciding(self):
        d = _make_decision(state=DecisionState.DEBATING.value)
        d.transition_to(DecisionState.DECIDING.value)
        assert d.state == DecisionState.DECIDING.value

    def test_deciding_to_risk_review(self):
        d = _make_decision(state=DecisionState.DECIDING.value)
        d.transition_to(DecisionState.RISK_REVIEW.value)
        assert d.state == DecisionState.RISK_REVIEW.value

    def test_risk_review_to_committee_review(self):
        d = _make_decision(state=DecisionState.RISK_REVIEW.value)
        d.transition_to(DecisionState.COMMITTEE_REVIEW.value)
        assert d.state == DecisionState.COMMITTEE_REVIEW.value

    def test_committee_review_to_approved(self):
        d = _make_decision(state=DecisionState.COMMITTEE_REVIEW.value)
        d.transition_to(DecisionState.APPROVED.value)
        assert d.state == DecisionState.APPROVED.value
        assert d.is_terminal

    def test_committee_review_to_rejected(self):
        d = _make_decision(state=DecisionState.COMMITTEE_REVIEW.value)
        d.transition_to(DecisionState.REJECTED.value)
        assert d.state == DecisionState.REJECTED.value
        assert d.is_terminal

    def test_deciding_to_revised(self):
        d = _make_decision(state=DecisionState.DECIDING.value)
        d.transition_to(DecisionState.REVISED.value)
        assert d.state == DecisionState.REVISED.value

    def test_revised_to_analyzing(self):
        d = _make_decision(state=DecisionState.REVISED.value)
        d.transition_to(DecisionState.ANALYZING.value)
        assert d.state == DecisionState.ANALYZING.value

    def test_suspended_to_analyzing(self):
        d = _make_decision(state=DecisionState.SUSPENDED.value)
        d.transition_to(DecisionState.ANALYZING.value)
        assert d.state == DecisionState.ANALYZING.value

    def test_invalid_transition_raises(self):
        d = _make_decision()
        with pytest.raises(InvalidTransitionError):
            d.transition_to(DecisionState.APPROVED.value)

    def test_proposed_to_approved_invalid(self):
        d = _make_decision()
        with pytest.raises(InvalidTransitionError):
            d.transition_to(DecisionState.APPROVED.value)

    def test_approved_is_terminal(self):
        d = _make_decision(state=DecisionState.APPROVED.value)
        assert d.is_terminal
        assert not d.can_transition_to(DecisionState.ANALYZING.value)

    def test_rejected_is_terminal(self):
        d = _make_decision(state=DecisionState.REJECTED.value)
        assert d.is_terminal

    def test_transition_updates_timestamp(self):
        d = _make_decision()
        old_ts = d.updated_at
        d.transition_to(DecisionState.ANALYZING.value)
        assert d.updated_at >= old_ts


class TestAnalystOutputRecording:
    """Analyst output recording on aggregate."""

    def test_record_analyst_output(self):
        d = _make_decision()
        output = _make_analyst_output("FUNDAMENTAL", 8.0)
        d.record_analyst_output(output)
        assert len(d.analyst_outputs) == 1
        assert d.analyst_outputs[0].analyst_type == "FUNDAMENTAL"

    def test_record_multiple_analysts(self):
        d = _make_decision()
        for atype in ["FUNDAMENTAL", "TECHNICAL", "SENTIMENT", "RISK", "MARKET"]:
            d.record_analyst_output(_make_analyst_output(atype, 7.0))
        assert len(d.analyst_outputs) == 5

    def test_duplicate_analyst_rejected(self):
        d = _make_decision()
        d.record_analyst_output(_make_analyst_output("FUNDAMENTAL", 8.0))
        with pytest.raises(DuplicateAnalystError):
            d.record_analyst_output(_make_analyst_output("FUNDAMENTAL", 7.0))

    def test_analyst_scores_property(self):
        d = _make_decision()
        d.record_analyst_output(_make_analyst_output("FUNDAMENTAL", 8.0))
        d.record_analyst_output(_make_analyst_output("TECHNICAL", 6.0))
        assert d.analyst_scores == [8.0, 6.0]


class TestDebateRecording:
    """Debate round recording."""

    def test_record_debate(self):
        d = _make_decision()
        debate = _make_debate()
        d.record_debate(debate)
        assert len(d.debate_rounds) == 1
        assert d.latest_debate.round_number == 1

    def test_latest_debate_property(self):
        d = _make_decision()
        assert d.latest_debate is None
        d.record_debate(_make_debate())
        assert d.latest_debate is not None


class TestMemoAndConviction:
    """Memo and conviction setting."""

    def test_set_memo(self):
        d = _make_decision()
        memo = _make_memo()
        d.set_memo(memo)
        assert d.memo is not None
        assert d.memo.ticker == "BBCA"
        assert d.memo.decision == "BUY"

    def test_set_conviction(self):
        d = _make_decision()
        conviction = ConvictionScore(level="STRONG", numeric_score=8.5, analyst_agreement=4)
        d.set_conviction(conviction)
        assert d.conviction.level == "STRONG"
        assert d.conviction.numeric_score == 8.5


class TestRepository:
    """In-memory repository tests."""

    def test_save_and_retrieve(self):
        from karsa.investment_workflow.infrastructure.persistence.in_memory_investment_decision_repository import (
            InMemoryInvestmentDecisionRepository,
        )

        repo = InMemoryInvestmentDecisionRepository()
        d = _make_decision()
        assert repo.save(d) is True

        loaded = repo.get_by_id(d.decision_id)
        assert loaded is not None
        assert loaded.ticker == "BBCA"

    def test_duplicate_save_returns_false(self):
        from karsa.investment_workflow.infrastructure.persistence.in_memory_investment_decision_repository import (
            InMemoryInvestmentDecisionRepository,
        )

        repo = InMemoryInvestmentDecisionRepository()
        d = _make_decision()
        assert repo.save(d) is True
        assert repo.save(d) is False

    def test_get_by_family_and_ticker(self):
        from karsa.investment_workflow.infrastructure.persistence.in_memory_investment_decision_repository import (
            InMemoryInvestmentDecisionRepository,
        )

        repo = InMemoryInvestmentDecisionRepository()
        d1 = _make_decision(decision_id="d-001", decision_date="2026-01-01")
        d2 = _make_decision(decision_id="d-002", decision_date="2026-06-01")
        repo.save(d1)
        repo.save(d2)

        results = repo.get_by_family_and_ticker("family-001", "BBCA")
        assert len(results) == 2
