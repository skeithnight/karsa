"""Tests for InvestmentDecisionService -- Sprint-13. ADR-140.

Covers:
- propose decision
- record analyst output
- record debate
- create memo
- approve decision
- reject decision
- revise decision
- outbox event creation
- duplicate detection
"""

import pytest
from decimal import Decimal

from karsa.investment_workflow.infrastructure.persistence.in_memory_investment_outbox_repository import (
    InMemoryInvestmentOutboxRepository,
)
from karsa.investment_workflow.application.investment_decision_service import (
    AnalystCommand,
    DecisionCommand,
    DecisionResult,
    DebateCommand,
    InvestmentDecisionService,
    MemoCommand,
)
from karsa.investment_workflow.domain.value_objects.conviction_score import (
    ConvictionScore,
)
from karsa.investment_workflow.domain.value_objects.enums import (
    AnalystType,
    ConvictionLevel,
    DecisionState,
    DecisionType,
)
from karsa.investment_workflow.infrastructure.persistence.in_memory_investment_decision_repository import (
    InMemoryInvestmentDecisionRepository,
)


def _make_service():
    decision_repo = InMemoryInvestmentDecisionRepository()
    outbox_repo = InMemoryInvestmentOutboxRepository()
    service = InvestmentDecisionService(
        decision_repo=decision_repo,
        outbox_repo=outbox_repo,
    )
    return service, decision_repo, outbox_repo


def _propose(service):
    cmd = DecisionCommand(
        capability_family_id="family-001",
        ticker="BBCA",
        decision_date="2026-06-21",
        proposed_by="test-user",
    )
    return service.propose_decision(cmd)


class TestProposeDecision:
    """Create a new investment decision."""

    def test_propose_success(self):
        service, _, _ = _make_service()
        result = _propose(service)
        assert result.success is True
        assert result.decision_id is not None
        assert result.message == "Decision proposed"

    def test_propose_creates_outbox_event(self):
        service, _, outbox_repo = _make_service()
        _propose(service)
        pending = outbox_repo.get_pending()
        assert len(pending) == 1
        assert pending[0].event_type == "InvestmentDecisionProposedEvent"

    def test_duplicate_propose_rejected(self):
        service, _, _ = _make_service()
        r1 = _propose(service)
        r2 = _propose(service)
        assert r1.success is True
        assert r2.success is False
        assert "Duplicate" in r2.message

    def test_propose_saves_to_repository(self):
        service, decision_repo, _ = _make_service()
        result = _propose(service)
        decision = decision_repo.get_by_id(result.decision_id)
        assert decision is not None
        assert decision.ticker == "BBCA"
        assert decision.state == DecisionState.PROPOSED.value


def _propose_and_analyze(service, decision_repo):
    """Helper: propose decision and transition to ANALYZING."""
    prop = _propose(service)
    decision = decision_repo.get_by_id(prop.decision_id)
    decision.transition_to(DecisionState.ANALYZING.value)
    decision_repo.save(decision)
    return prop


class TestRecordAnalystOutput:
    """Record analyst output on a decision."""

    def test_record_analyst_success(self):
        service, decision_repo, _ = _make_service()
        prop = _propose_and_analyze(service, decision_repo)

        cmd = AnalystCommand(
            decision_id=prop.decision_id,
            analyst_type=AnalystType.FUNDAMENTAL.value,
            score=8.0,
            confidence=0.9,
            output_text="Strong fundamentals: P/E 15.8x, ROE 18.2%",
            tools_used=["YFinance"],
        )
        result = service.record_analyst_output(cmd)
        assert result.success is True
        assert "FUNDAMENTAL" in result.message

    def test_record_multiple_analysts(self):
        service, decision_repo, _ = _make_service()
        prop = _propose_and_analyze(service, decision_repo)

        for atype in AnalystType:
            cmd = AnalystCommand(
                decision_id=prop.decision_id,
                analyst_type=atype.value,
                score=7.0,
                confidence=0.8,
                output_text=f"Analysis output for {atype.value}",
            )
            result = service.record_analyst_output(cmd)
            assert result.success is True

        decision = decision_repo.get_by_id(prop.decision_id)
        assert len(decision.analyst_outputs) == 5

    def test_duplicate_analyst_rejected(self):
        service, decision_repo, _ = _make_service()
        prop = _propose_and_analyze(service, decision_repo)

        cmd = AnalystCommand(
            decision_id=prop.decision_id,
            analyst_type=AnalystType.FUNDAMENTAL.value,
            score=8.0,
            confidence=0.9,
            output_text="First analysis",
        )
        service.record_analyst_output(cmd)

        cmd2 = AnalystCommand(
            decision_id=prop.decision_id,
            analyst_type=AnalystType.FUNDAMENTAL.value,
            score=7.0,
            confidence=0.8,
            output_text="Second analysis",
        )
        result = service.record_analyst_output(cmd2)
        assert result.success is False
        assert "already recorded" in result.message

    def test_analyst_creates_outbox_event(self):
        service, decision_repo, outbox_repo = _make_service()
        prop = _propose_and_analyze(service, decision_repo)

        cmd = AnalystCommand(
            decision_id=prop.decision_id,
            analyst_type=AnalystType.TECHNICAL.value,
            score=6.5,
            confidence=0.7,
            output_text="RSI 55, above 50-day MA",
        )
        service.record_analyst_output(cmd)

        pending = outbox_repo.get_pending()
        event_types = [e.event_type for e in pending]
        assert "AnalystOutputRecordedEvent" in event_types

    def test_analyst_on_missing_decision(self):
        service, _, _ = _make_service()
        cmd = AnalystCommand(
            decision_id="nonexistent",
            analyst_type=AnalystType.FUNDAMENTAL.value,
            score=8.0,
            confidence=0.9,
            output_text="Analysis",
        )
        result = service.record_analyst_output(cmd)
        assert result.success is False
        assert "not found" in result.message

    def test_analyst_rejected_in_wrong_state(self):
        """State guard: analyst can only be recorded in ANALYZING state."""
        service, _, _ = _make_service()
        prop = _propose(service)  # stays in PROPOSED

        cmd = AnalystCommand(
            decision_id=prop.decision_id,
            analyst_type=AnalystType.FUNDAMENTAL.value,
            score=8.0,
            confidence=0.9,
            output_text="Analysis",
        )
        result = service.record_analyst_output(cmd)
        assert result.success is False
        assert "ANALYZING" in result.message


class TestRecordDebate:
    """Record debate round on a decision."""

    def test_record_debate_success(self):
        service, decision_repo, _ = _make_service()
        prop = _propose(service)
        # Transition to DEBATING
        decision = decision_repo.get_by_id(prop.decision_id)
        decision.transition_to(DecisionState.ANALYZING.value)
        decision.transition_to(DecisionState.DEBATING.value)
        decision_repo.save(decision)

        cmd = DebateCommand(
            decision_id=prop.decision_id,
            round_number=1,
            bull_memo="Strong fundamentals and technicals support buy thesis at current price levels with good entry",
            bear_memo="Macro headwinds and valuation concerns suggest caution at current price levels for entry",
            bull_conviction=ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3),
            bear_conviction=ConvictionScore(level="WEAK", numeric_score=3.0, analyst_agreement=1),
        )
        result = service.record_debate(cmd)
        assert result.success is True

        decision = decision_repo.get_by_id(prop.decision_id)
        assert len(decision.debate_rounds) == 1

    def test_debate_creates_outbox_event(self):
        service, decision_repo, outbox_repo = _make_service()
        prop = _propose(service)
        decision = decision_repo.get_by_id(prop.decision_id)
        decision.transition_to(DecisionState.ANALYZING.value)
        decision.transition_to(DecisionState.DEBATING.value)
        decision_repo.save(decision)

        cmd = DebateCommand(
            decision_id=prop.decision_id,
            round_number=1,
            bull_memo="Strong fundamentals and technicals support buy thesis at current price levels with good entry",
            bear_memo="Macro headwinds and valuation concerns suggest caution at current price levels for entry",
            bull_conviction=ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3),
            bear_conviction=ConvictionScore(level="WEAK", numeric_score=3.0, analyst_agreement=1),
        )
        service.record_debate(cmd)

        pending = outbox_repo.get_pending()
        event_types = [e.event_type for e in pending]
        assert "DebateCompletedEvent" in event_types


class TestCreateMemo:
    """Create investment memo and transition to RISK_REVIEW."""

    def test_create_memo_success(self):
        service, decision_repo, _ = _make_service()
        prop = _propose(service)

        # Transition to DECIDING first
        decision = decision_repo.get_by_id(prop.decision_id)
        decision.transition_to(DecisionState.ANALYZING.value)
        decision.transition_to(DecisionState.DEBATING.value)
        decision.transition_to(DecisionState.DECIDING.value)
        decision_repo.save(decision)

        cmd = MemoCommand(
            decision_id=prop.decision_id,
            ticker="BBCA",
            decision=DecisionType.BUY.value,
            conviction=ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3),
            thesis="BBCA offers strong dividend yield and growth potential with reasonable valuation entry point",
            entry_price=8500.0,
            exit_target=9200.0,
            position_size_pct=2.5,
        )
        result = service.create_memo(cmd)
        assert result.success is True
        assert "risk review" in result.message.lower()

        decision = decision_repo.get_by_id(prop.decision_id)
        assert decision.state == DecisionState.RISK_REVIEW.value
        assert decision.memo is not None
        assert decision.memo.ticker == "BBCA"

    def test_create_memo_creates_outbox_event(self):
        service, decision_repo, outbox_repo = _make_service()
        prop = _propose(service)

        decision = decision_repo.get_by_id(prop.decision_id)
        decision.transition_to(DecisionState.ANALYZING.value)
        decision.transition_to(DecisionState.DEBATING.value)
        decision.transition_to(DecisionState.DECIDING.value)
        decision_repo.save(decision)

        cmd = MemoCommand(
            decision_id=prop.decision_id,
            ticker="BBCA",
            decision=DecisionType.BUY.value,
            conviction=ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3),
            thesis="BBCA offers strong dividend yield and growth potential with reasonable valuation entry point",
        )
        service.create_memo(cmd)

        pending = outbox_repo.get_pending()
        event_types = [e.event_type for e in pending]
        assert "DecisionMemoCreatedEvent" in event_types

    def test_create_memo_rejected_in_wrong_state(self):
        """State guard: memo can only be created in DECIDING state."""
        service, _, _ = _make_service()
        prop = _propose(service)  # stays in PROPOSED

        cmd = MemoCommand(
            decision_id=prop.decision_id,
            ticker="BBCA",
            decision=DecisionType.BUY.value,
            conviction=ConvictionScore(level="STRONG", numeric_score=8.0, analyst_agreement=3),
            thesis="BBCA offers strong dividend yield and growth potential with reasonable valuation entry point",
        )
        result = service.create_memo(cmd)
        assert result.success is False
        assert "DECIDING" in result.message


class TestApproveDecision:
    """Approve a decision."""

    def test_approve_success(self):
        service, decision_repo, _ = _make_service()
        prop = _propose(service)

        decision = decision_repo.get_by_id(prop.decision_id)
        for state in ["ANALYZING", "DEBATING", "DECIDING", "RISK_REVIEW", "COMMITTEE_REVIEW"]:
            decision.transition_to(state)
        decision_repo.save(decision)

        result = service.approve_decision(prop.decision_id, "committee-chair")
        assert result.success is True
        assert result.message == "Decision approved"

        decision = decision_repo.get_by_id(prop.decision_id)
        assert decision.state == DecisionState.APPROVED.value

    def test_approve_invalid_transition(self):
        service, _, _ = _make_service()
        prop = _propose(service)

        result = service.approve_decision(prop.decision_id, "committee-chair")
        assert result.success is False


class TestRejectDecision:
    """Reject a decision."""

    def test_reject_success(self):
        service, decision_repo, _ = _make_service()
        prop = _propose(service)

        result = service.reject_decision(
            prop.decision_id, "risk-officer", "Mandate violation"
        )
        assert result.success is True

        decision = decision_repo.get_by_id(prop.decision_id)
        assert decision.state == DecisionState.REJECTED.value
        assert decision.is_terminal


class TestReviseDecision:
    """Revise a decision."""

    def test_revise_success(self):
        service, decision_repo, _ = _make_service()
        prop = _propose(service)

        decision = decision_repo.get_by_id(prop.decision_id)
        for state in ["ANALYZING", "DEBATING", "DECIDING"]:
            decision.transition_to(state)
        decision_repo.save(decision)

        result = service.revise_decision(
            prop.decision_id, "Reduce position size"
        )
        assert result.success is True

        decision = decision_repo.get_by_id(prop.decision_id)
        assert decision.state == DecisionState.REVISED.value

    def test_revise_to_analyzing(self):
        service, decision_repo, _ = _make_service()
        prop = _propose(service)

        decision = decision_repo.get_by_id(prop.decision_id)
        for state in ["ANALYZING", "DEBATING", "DECIDING"]:
            decision.transition_to(state)
        decision.transition_to("REVISED")
        decision_repo.save(decision)

        # Can go back to ANALYZING
        decision = decision_repo.get_by_id(prop.decision_id)
        decision.transition_to("ANALYZING")
        assert decision.state == DecisionState.ANALYZING.value
