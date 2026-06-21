"""Tests for investment workflow facades -- Sprint-13. ADR-140.

Covers:
- Command facade: propose, analyst, debate, memo, approve, reject, revise
- Query facade: get decision, get by ticker, get by family
- No domain leakage through facade API
"""

import pytest
from datetime import datetime

from karsa.investment_workflow.integration.investment_workflow_bootstrap import (
    bootstrap,
)
from karsa.investment_workflow.integration.investment_workflow_command_facade import (
    CommandResult,
)
from karsa.investment_workflow.integration.investment_workflow_query_facade import (
    DecisionDTO,
)


@pytest.fixture
def ctx():
    return bootstrap()


class TestCommandFacade:
    """Command facade operations."""

    def test_propose_decision(self, ctx):
        result = ctx.command_facade.propose_decision(
            capability_family_id="family-001",
            ticker="BBCA",
            decision_date="2026-06-21",
            proposed_by="test-user",
        )
        assert result.success is True
        assert result.data is not None
        assert "decision_id" in result.data

    def test_record_analyst(self, ctx):
        prop = ctx.command_facade.propose_decision(
            capability_family_id="family-001",
            ticker="BBCA",
            decision_date="2026-06-21",
        )
        decision_id = prop.data["decision_id"]

        # Transition to ANALYZING
        decision = ctx.decision_repo.get_by_id(decision_id)
        decision.transition_to("ANALYZING")
        ctx.decision_repo.save(decision)

        result = ctx.command_facade.record_analyst(
            decision_id=decision_id,
            analyst_type="FUNDAMENTAL",
            score=8.0,
            confidence=0.9,
            output_text="Strong fundamentals with good valuation metrics",
        )
        assert result.success is True

    def test_full_workflow(self, ctx):
        """End-to-end: propose → analyze → debate → memo → approve."""
        # Propose
        prop = ctx.command_facade.propose_decision(
            capability_family_id="family-001",
            ticker="BBCA",
            decision_date="2026-06-21",
        )
        decision_id = prop.data["decision_id"]

        # Transition to ANALYZING
        decision = ctx.decision_repo.get_by_id(decision_id)
        decision.transition_to("ANALYZING")
        ctx.decision_repo.save(decision)

        # Record analysts
        for atype in ["FUNDAMENTAL", "TECHNICAL", "SENTIMENT"]:
            ctx.command_facade.record_analyst(
                decision_id=decision_id,
                analyst_type=atype,
                score=7.5,
                confidence=0.8,
                output_text=f"{atype} analysis output with sufficient detail for decision",
            )

        # Transition to DEBATING
        decision = ctx.decision_repo.get_by_id(decision_id)
        decision.transition_to("DEBATING")
        ctx.decision_repo.save(decision)

        # Record debate
        ctx.command_facade.record_debate(
            decision_id=decision_id,
            round_number=1,
            bull_memo="Strong fundamentals and technicals support buy thesis at current price levels with good entry",
            bear_memo="Macro headwinds and valuation concerns suggest caution at current price levels for entry",
            bull_level="STRONG",
            bull_score=8.0,
            bull_agreement=3,
            bear_level="WEAK",
            bear_score=3.0,
            bear_agreement=1,
        )

        # Transition to DECIDING
        decision = ctx.decision_repo.get_by_id(decision_id)
        decision.transition_to("DECIDING")
        ctx.decision_repo.save(decision)

        # Create memo
        memo_result = ctx.command_facade.create_memo(
            decision_id=decision_id,
            ticker="BBCA",
            decision="BUY",
            conviction_level="STRONG",
            conviction_score=8.0,
            conviction_agreement=3,
            thesis="BBCA offers strong dividend yield and growth potential with reasonable valuation entry point",
            entry_price=8500.0,
            exit_target=9200.0,
            position_size_pct=2.5,
        )
        assert memo_result.success is True

        # Transition through risk and committee review
        decision = ctx.decision_repo.get_by_id(decision_id)
        decision.transition_to("COMMITTEE_REVIEW")
        ctx.decision_repo.save(decision)

        # Approve
        approve_result = ctx.command_facade.approve(
            decision_id, "committee-chair"
        )
        assert approve_result.success is True

        # Verify via query
        dto = ctx.query_facade.get_decision(decision_id)
        assert dto.state == "APPROVED"
        assert dto.has_memo is True
        assert dto.conviction_level == "STRONG"
        assert dto.memo_decision == "BUY"

    def test_reject_decision(self, ctx):
        prop = ctx.command_facade.propose_decision(
            capability_family_id="family-001",
            ticker="BBCA",
            decision_date="2026-06-21",
        )
        decision_id = prop.data["decision_id"]

        result = ctx.command_facade.reject(
            decision_id, "risk-officer", "Mandate violation"
        )
        assert result.success is True

    def test_revise_decision(self, ctx):
        prop = ctx.command_facade.propose_decision(
            capability_family_id="family-001",
            ticker="BBCA",
            decision_date="2026-06-21",
        )
        decision_id = prop.data["decision_id"]

        # Transition to DECIDING
        decision = ctx.decision_repo.get_by_id(decision_id)
        decision.transition_to("ANALYZING")
        decision.transition_to("DEBATING")
        decision.transition_to("DECIDING")
        ctx.decision_repo.save(decision)

        result = ctx.command_facade.revise(
            decision_id, "Reduce position size"
        )
        assert result.success is True


class TestQueryFacade:
    """Query facade operations."""

    def test_get_decision(self, ctx):
        prop = ctx.command_facade.propose_decision(
            capability_family_id="family-001",
            ticker="BBCA",
            decision_date="2026-06-21",
            proposed_by="test-user",
        )
        decision_id = prop.data["decision_id"]

        dto = ctx.query_facade.get_decision(decision_id)
        assert dto is not None
        assert isinstance(dto, DecisionDTO)
        assert dto.ticker == "BBCA"
        assert dto.state == "PROPOSED"

    def test_get_decision_not_found(self, ctx):
        dto = ctx.query_facade.get_decision("nonexistent")
        assert dto is None

    def test_get_decisions_by_ticker(self, ctx):
        ctx.command_facade.propose_decision(
            capability_family_id="family-001",
            ticker="BBCA",
            decision_date="2026-01-01",
        )
        ctx.command_facade.propose_decision(
            capability_family_id="family-001",
            ticker="BBCA",
            decision_date="2026-06-01",
        )
        ctx.command_facade.propose_decision(
            capability_family_id="family-001",
            ticker="ASII",
            decision_date="2026-06-01",
        )

        results = ctx.query_facade.get_decisions_by_ticker("BBCA")
        assert len(results) == 2
        assert all(d.ticker == "BBCA" for d in results)

    def test_get_decisions_by_family(self, ctx):
        ctx.command_facade.propose_decision(
            capability_family_id="family-001",
            ticker="BBCA",
            decision_date="2026-01-01",
        )
        ctx.command_facade.propose_decision(
            capability_family_id="family-001",
            ticker="ASII",
            decision_date="2026-06-01",
        )
        ctx.command_facade.propose_decision(
            capability_family_id="family-002",
            ticker="BBCA",
            decision_date="2026-06-01",
        )

        results = ctx.query_facade.get_decisions_by_family("family-001")
        assert len(results) == 2

    def test_dto_has_no_domain_types(self, ctx):
        """DTO must not expose domain internals."""
        prop = ctx.command_facade.propose_decision(
            capability_family_id="family-001",
            ticker="BBCA",
            decision_date="2026-06-21",
        )
        dto = ctx.query_facade.get_decision(prop.data["decision_id"])

        # DTO should be a frozen dataclass with only primitive fields
        data = dto.__dict__
        for key, value in data.items():
            if value is not None:
                assert isinstance(
                    value, (str, int, float, bool, datetime)
                ), f"Field {key} has non-primitive type {type(value)}"

    def test_dto_reflects_state_changes(self, ctx):
        prop = ctx.command_facade.propose_decision(
            capability_family_id="family-001",
            ticker="BBCA",
            decision_date="2026-06-21",
        )
        decision_id = prop.data["decision_id"]

        # Initial state
        dto = ctx.query_facade.get_decision(decision_id)
        assert dto.state == "PROPOSED"
        assert dto.analyst_count == 0

        # Transition and record analyst
        decision = ctx.decision_repo.get_by_id(decision_id)
        decision.transition_to("ANALYZING")
        ctx.decision_repo.save(decision)

        ctx.command_facade.record_analyst(
            decision_id=decision_id,
            analyst_type="FUNDAMENTAL",
            score=8.0,
            confidence=0.9,
            output_text="Strong fundamentals with good valuation metrics",
        )

        dto = ctx.query_facade.get_decision(decision_id)
        assert dto.state == "ANALYZING"
        assert dto.analyst_count == 1
