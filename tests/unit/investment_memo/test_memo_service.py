"""Tests for MemoService -- Sprint-15.

Covers:
- create memo
- activate memo
- revise memo
- close position
- invalidate memo
- lifecycle end-to-end
"""

import pytest
from datetime import date
from decimal import Decimal

from karsa.investment_memo.application.memo_service import (
    ClosePositionCommand,
    CreateMemoCommand,
    MemoService,
    MemoResult,
)
from karsa.investment_memo.domain.value_objects.enums import (
    ConvictionLevel,
    MemoDecision,
    MemoStatus,
)
from karsa.investment_memo.infrastructure.persistence.in_memory_investment_memo_repository import (
    InMemoryInvestmentMemoRepository,
)


def _make_service():
    repo = InMemoryInvestmentMemoRepository()
    return MemoService(memo_repo=repo), repo


def _create_memo(service, **overrides):
    defaults = dict(
        decision_id="decision-001",
        ticker="BBCA",
        decision=MemoDecision.BUY.value,
        conviction_level=ConvictionLevel.STRONG.value,
        conviction_score=8.0,
        thesis="BBCA offers strong dividend yield and growth potential with reasonable valuation",
        entry_price=8500.0,
        exit_target=9200.0,
    )
    defaults.update(overrides)
    cmd = CreateMemoCommand(**defaults)
    return service.create_memo(cmd)


class TestCreateMemo:
    """Create investment memo."""

    def test_create_success(self):
        service, _ = _make_service()
        result = _create_memo(service)
        assert result.success is True
        assert result.memo_id is not None

    def test_create_saves_to_repo(self):
        service, repo = _make_service()
        result = _create_memo(service)
        memo = repo.get_by_id(result.memo_id)
        assert memo is not None
        assert memo.ticker == "BBCA"
        assert memo.status == MemoStatus.DRAFT.value

    def test_duplicate_rejected(self):
        service, _ = _make_service()
        r1 = _create_memo(service, decision_id="d-001")
        r2 = _create_memo(service, decision_id="d-001")
        assert r1.success is True
        assert r2.success is False

    def test_create_with_metadata(self):
        service, repo = _make_service()
        result = _create_memo(
            service,
            key_metrics={"pe": 15.8, "dividend_yield": 3.5},
            risks=["Interest rate cuts", "MSCI downgrade"],
        )
        memo = repo.get_by_id(result.memo_id)
        assert memo.key_metrics["pe"] == 15.8
        assert len(memo.risks) == 2


class TestActivateMemo:
    """Activate memo (DRAFT → ACTIVE)."""

    def test_activate_success(self):
        service, repo = _make_service()
        result = _create_memo(service)
        activate_result = service.activate_memo(result.memo_id)
        assert activate_result.success is True

        memo = repo.get_by_id(result.memo_id)
        assert memo.status == MemoStatus.ACTIVE.value

    def test_activate_nonexistent(self):
        service, _ = _make_service()
        result = service.activate_memo("nonexistent")
        assert result.success is False


class TestReviseMemo:
    """Revise memo thesis and conviction."""

    def test_revise_success(self):
        service, repo = _make_service()
        result = _create_memo(service)

        revise_result = service.revise_memo(
            result.memo_id,
            thesis="Updated thesis with new data and revised conviction level assessment for the position",
            conviction_level=ConvictionLevel.MEDIUM.value,
            revised_by="pm-user",
            reason="New data",
        )
        assert revise_result.success is True

        memo = repo.get_by_id(result.memo_id)
        assert memo.revision_count == 1

    def test_cannot_revise_closed(self):
        service, repo = _make_service()
        result = _create_memo(service)
        memo = repo.get_by_id(result.memo_id)
        memo.transition_to(MemoStatus.ACTIVE.value)
        memo.close_position(
            _make_realized_return()
        )
        repo.save(memo)

        revise_result = service.revise_memo(
            result.memo_id,
            thesis="Attempt to revise closed memo with sufficient length for validation",
            conviction_level=ConvictionLevel.WEAK.value,
            revised_by="pm-user",
        )
        assert revise_result.success is False


class TestClosePosition:
    """Close position with realized return."""

    def test_close_success(self):
        service, repo = _make_service()
        result = _create_memo(service)
        memo = repo.get_by_id(result.memo_id)
        memo.transition_to(MemoStatus.ACTIVE.value)
        repo.save(memo)

        close_cmd = ClosePositionCommand(
            memo_id=result.memo_id,
            exit_price=9200.0,
            quantity=1000,
            close_reason="TARGET_HIT",
        )
        close_result = service.close_position(close_cmd)
        assert close_result.success is True

        memo = repo.get_by_id(result.memo_id)
        assert memo.status == MemoStatus.CLOSED.value
        assert memo.has_realized_return

    def test_close_nonexistent(self):
        service, _ = _make_service()
        close_cmd = ClosePositionCommand(
            memo_id="nonexistent",
            exit_price=9200.0,
            quantity=1000,
        )
        result = service.close_position(close_cmd)
        assert result.success is False

    def test_close_draft_fails(self):
        service, _ = _make_service()
        result = _create_memo(service)

        close_cmd = ClosePositionCommand(
            memo_id=result.memo_id,
            exit_price=9200.0,
            quantity=1000,
        )
        close_result = service.close_position(close_cmd)
        assert close_result.success is False
        assert "DRAFT" in close_result.message


class TestInvalidateMemo:
    """Invalidate memo (thesis broken)."""

    def test_invalidate_success(self):
        service, repo = _make_service()
        result = _create_memo(service)

        inv_result = service.invalidate_memo(
            result.memo_id, "Dividend cut announced"
        )
        assert inv_result.success is True

        memo = repo.get_by_id(result.memo_id)
        assert memo.status == MemoStatus.INVALIDATED.value
        assert memo.is_terminal


class TestLifecycleEndToEnd:
    """Full memo lifecycle: create → activate → revise → close."""

    def test_full_lifecycle(self):
        service, repo = _make_service()

        # Create
        create_result = _create_memo(service)
        assert create_result.success is True

        # Activate
        activate_result = service.activate_memo(create_result.memo_id)
        assert activate_result.success is True

        # Revise
        revise_result = service.revise_memo(
            create_result.memo_id,
            thesis="Revised thesis after new quarterly results with updated conviction and risk assessment",
            conviction_level=ConvictionLevel.MEDIUM.value,
            revised_by="pm-user",
            reason="Q2 results",
        )
        assert revise_result.success is True

        # Close
        close_result = service.close_position(ClosePositionCommand(
            memo_id=create_result.memo_id,
            exit_price=9200.0,
            quantity=1000,
            close_reason="TARGET_HIT",
        ))
        assert close_result.success is True

        # Verify final state
        memo = repo.get_by_id(create_result.memo_id)
        assert memo.status == MemoStatus.CLOSED.value
        assert memo.revision_count == 1
        assert memo.has_realized_return
        assert memo.realized_return.realized_return_pct > 0


def _make_realized_return():
    from karsa.investment_memo.domain.value_objects.realized_return import (
        RealizedReturn,
    )
    return RealizedReturn(
        ticker="BBCA",
        entry_date=date(2026, 1, 1),
        entry_price=Decimal("8500"),
        exit_date=date(2026, 6, 1),
        exit_price=Decimal("9200"),
        quantity=1000,
        realized_pnl=Decimal("700000"),
        realized_return_pct=8.2353,
        holding_period_days=151,
        close_reason="TARGET_HIT",
    )
