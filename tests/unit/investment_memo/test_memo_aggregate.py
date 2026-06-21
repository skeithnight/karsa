"""Tests for InvestmentMemo aggregate -- Sprint-15.

Covers:
- aggregate creation
- state transitions
- revision tracking
- position closing
- invalidation
- realized return
"""

import pytest
from datetime import date, datetime
from decimal import Decimal

from karsa.investment_memo.domain.aggregates.investment_memo import (
    InvestmentMemo,
)
from karsa.investment_memo.domain.exceptions import (
    InvalidMemoError,
    MemoStateError,
)
from karsa.investment_memo.domain.value_objects.enums import (
    ConvictionLevel,
    MemoDecision,
    MemoStatus,
)
from karsa.investment_memo.domain.value_objects.realized_return import (
    RealizedReturn,
)


def _make_memo(**overrides):
    defaults = dict(
        memo_id="urn:karsa:memo:test001",
        decision_id="decision-001",
        ticker="BBCA",
        decision=MemoDecision.BUY.value,
        conviction_level=ConvictionLevel.STRONG.value,
        conviction_score=8.0,
        thesis="BBCA offers strong dividend yield and growth potential with reasonable valuation",
    )
    defaults.update(overrides)
    return InvestmentMemo(**defaults)


def _make_realized_return(**overrides):
    defaults = dict(
        ticker="BBCA",
        entry_date=date(2026, 1, 1),
        entry_price=Decimal("8500"),
        exit_date=date(2026, 6, 1),
        exit_price=Decimal("9200"),
        quantity=1000,
        realized_pnl=Decimal("700000"),
        realized_return_pct=8.2353,
        holding_period_days=151,
        target_price=Decimal("9200"),
        target_error_pct=0.0,
        close_reason="TARGET_HIT",
    )
    defaults.update(overrides)
    return RealizedReturn(**defaults)


class TestAggregateCreation:
    """InvestmentMemo aggregate creation."""

    def test_valid_memo(self):
        m = _make_memo()
        assert m.memo_id == "urn:karsa:memo:test001"
        assert m.ticker == "BBCA"
        assert m.status == MemoStatus.DRAFT.value

    def test_frozen_after_init(self):
        m = _make_memo()
        with pytest.raises(AttributeError):
            m.ticker = "ASII"

    def test_missing_memo_id(self):
        with pytest.raises(InvalidMemoError, match="memo_id"):
            _make_memo(memo_id="")

    def test_missing_ticker(self):
        with pytest.raises(InvalidMemoError, match="ticker"):
            _make_memo(ticker="")

    def test_invalid_decision(self):
        with pytest.raises(InvalidMemoError, match="decision"):
            _make_memo(decision="INVALID")

    def test_invalid_conviction(self):
        with pytest.raises(InvalidMemoError, match="conviction_level"):
            _make_memo(conviction_level="INVALID")

    def test_invalid_conviction_score(self):
        with pytest.raises(InvalidMemoError, match="conviction_score"):
            _make_memo(conviction_score=11.0)


class TestStateTransitions:
    """Memo state machine."""

    def test_draft_to_active(self):
        m = _make_memo()
        m.transition_to(MemoStatus.ACTIVE.value)
        assert m.status == MemoStatus.ACTIVE.value

    def test_active_to_closed(self):
        m = _make_memo(status=MemoStatus.ACTIVE.value)
        rr = _make_realized_return()
        m.close_position(rr)
        assert m.status == MemoStatus.CLOSED.value

    def test_draft_to_invalidated(self):
        m = _make_memo()
        m.invalidate("Thesis broken")
        assert m.status == MemoStatus.INVALIDATED.value

    def test_active_to_invalidated(self):
        m = _make_memo(status=MemoStatus.ACTIVE.value)
        m.invalidate("Thesis broken")
        assert m.status == MemoStatus.INVALIDATED.value

    def test_closed_is_terminal(self):
        m = _make_memo(status=MemoStatus.CLOSED.value)
        assert m.is_terminal
        assert not m.can_transition_to(MemoStatus.ACTIVE.value)

    def test_invalidated_is_terminal(self):
        m = _make_memo(status=MemoStatus.INVALIDATED.value)
        assert m.is_terminal

    def test_invalid_transition_raises(self):
        m = _make_memo()
        with pytest.raises(MemoStateError):
            m.transition_to(MemoStatus.CLOSED.value)

    def test_cannot_close_draft(self):
        m = _make_memo()
        rr = _make_realized_return()
        with pytest.raises(MemoStateError, match="DRAFT"):
            m.close_position(rr)

    def test_cannot_invalidate_closed(self):
        m = _make_memo(status=MemoStatus.CLOSED.value)
        with pytest.raises(MemoStateError):
            m.invalidate("Too late")


class TestRevisionTracking:
    """Memo revision history."""

    def test_add_revision(self):
        m = _make_memo()
        m.add_revision(
            thesis="Updated thesis with new analysis and conviction level change",
            conviction_level=ConvictionLevel.MEDIUM.value,
            revised_by="pm-user",
            reason="New data",
        )
        assert m.revision_count == 1
        assert m.thesis == "Updated thesis with new analysis and conviction level change"
        assert m.conviction_level == ConvictionLevel.MEDIUM.value

    def test_multiple_revisions(self):
        m = _make_memo()
        for i in range(3):
            m.add_revision(
                thesis=f"Revision {i+1} thesis with sufficient length for validation requirements",
                conviction_level=ConvictionLevel.STRONG.value,
                revised_by="pm-user",
            )
        assert m.revision_count == 3


class TestPositionClosing:
    """Close position with realized return."""

    def test_close_position(self):
        m = _make_memo(status=MemoStatus.ACTIVE.value)
        rr = _make_realized_return()
        m.close_position(rr)

        assert m.status == MemoStatus.CLOSED.value
        assert m.has_realized_return
        assert m.realized_return.realized_return_pct == pytest.approx(8.2353)

    def test_target_accuracy(self):
        m = _make_memo(status=MemoStatus.ACTIVE.value)
        rr = _make_realized_return(target_error_pct=2.5)
        m.close_position(rr)

        assert m.target_accuracy == pytest.approx(97.5)

    def test_no_target_accuracy_when_no_target(self):
        m = _make_memo(status=MemoStatus.ACTIVE.value)
        rr = _make_realized_return(target_price=None, target_error_pct=None)
        m.close_position(rr)

        assert m.target_accuracy is None


class TestRealizedReturn:
    """RealizedReturn value object."""

    def test_compute(self):
        rr = RealizedReturn.compute(
            ticker="BBCA",
            entry_date=date(2026, 1, 1),
            entry_price=Decimal("8500"),
            exit_date=date(2026, 6, 1),
            exit_price=Decimal("9200"),
            quantity=1000,
            target_price=Decimal("9200"),
            close_reason="TARGET_HIT",
        )
        assert rr.realized_return_pct == pytest.approx(8.2353)
        assert rr.holding_period_days == 151
        assert rr.target_error_pct == pytest.approx(0.0)

    def test_frozen(self):
        rr = _make_realized_return()
        with pytest.raises(AttributeError):
            rr.ticker = "ASII"

    def test_invalid_quantity(self):
        with pytest.raises(Exception):
            _make_realized_return(quantity=0)

    def test_invalid_price(self):
        with pytest.raises(Exception):
            _make_realized_return(entry_price=Decimal("0"))


class TestRepository:
    """In-memory repository tests."""

    def test_save_and_retrieve(self):
        from karsa.investment_memo.infrastructure.persistence.in_memory_investment_memo_repository import (
            InMemoryInvestmentMemoRepository,
        )

        repo = InMemoryInvestmentMemoRepository()
        m = _make_memo()
        assert repo.save(m) is True

        loaded = repo.get_by_id(m.memo_id)
        assert loaded is not None
        assert loaded.ticker == "BBCA"

    def test_duplicate_save_returns_false(self):
        from karsa.investment_memo.infrastructure.persistence.in_memory_investment_memo_repository import (
            InMemoryInvestmentMemoRepository,
        )

        repo = InMemoryInvestmentMemoRepository()
        m = _make_memo()
        assert repo.save(m) is True
        assert repo.save(m) is False

    def test_get_by_decision_id(self):
        from karsa.investment_memo.infrastructure.persistence.in_memory_investment_memo_repository import (
            InMemoryInvestmentMemoRepository,
        )

        repo = InMemoryInvestmentMemoRepository()
        m = _make_memo()
        repo.save(m)

        loaded = repo.get_by_decision_id("decision-001")
        assert loaded is not None

    def test_get_by_ticker(self):
        from karsa.investment_memo.infrastructure.persistence.in_memory_investment_memo_repository import (
            InMemoryInvestmentMemoRepository,
        )

        repo = InMemoryInvestmentMemoRepository()
        repo.save(_make_memo(memo_id="m-001", decision_id="d-001"))
        repo.save(_make_memo(memo_id="m-002", decision_id="d-002"))
        repo.save(_make_memo(
            memo_id="m-003", decision_id="d-003", ticker="ASII"
        ))

        results = repo.get_by_ticker("BBCA")
        assert len(results) == 2
