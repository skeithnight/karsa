"""MemoService -- Sprint-15.

Application service for investment memo lifecycle.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from karsa.investment_memo.domain.aggregates.investment_memo import (
    InvestmentMemo,
)
from karsa.investment_memo.domain.events.memo_events import (
    MemoActivatedEvent,
    MemoClosedEvent,
    MemoCreatedEvent,
    MemoInvalidatedEvent,
    MemoRevisedEvent,
)
from karsa.investment_memo.domain.exceptions import (
    DuplicateMemoError,
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
from karsa.investment_memo.infrastructure.repositories.investment_memo_repository import (
    InvestmentMemoRepository,
)


@dataclass
class CreateMemoCommand:
    """Input DTO for creating a memo."""

    decision_id: str
    ticker: str
    decision: str
    conviction_level: str
    conviction_score: float
    thesis: str
    entry_price: Optional[float] = None
    exit_target: Optional[float] = None
    stop_loss: Optional[float] = None
    position_size_pct: Optional[float] = None
    key_metrics: Optional[Dict[str, Any]] = None
    risks: Optional[List[str]] = None
    created_by: str = ""


@dataclass
class ClosePositionCommand:
    """Input DTO for closing a position."""

    memo_id: str
    exit_price: float
    quantity: int
    close_reason: str = "MANUAL"
    exit_date: Optional[date] = None


@dataclass
class MemoResult:
    """Output DTO from memo operations."""

    success: bool
    message: str
    memo_id: Optional[str] = None
    events: Optional[List] = None


class MemoService:
    """Application service for investment memo lifecycle."""

    def __init__(
        self, memo_repo: InvestmentMemoRepository
    ) -> None:
        self._memo_repo = memo_repo

    def create_memo(self, command: CreateMemoCommand) -> MemoResult:
        """Create an investment memo."""
        memo_id = f"urn:karsa:memo:{uuid.uuid4().hex}"

        memo = InvestmentMemo(
            memo_id=memo_id,
            decision_id=command.decision_id,
            ticker=command.ticker,
            decision=command.decision,
            conviction_level=command.conviction_level,
            conviction_score=command.conviction_score,
            thesis=command.thesis,
            entry_price=(
                Decimal(str(command.entry_price))
                if command.entry_price
                else None
            ),
            exit_target=(
                Decimal(str(command.exit_target))
                if command.exit_target
                else None
            ),
            stop_loss=(
                Decimal(str(command.stop_loss))
                if command.stop_loss
                else None
            ),
            position_size_pct=command.position_size_pct,
            key_metrics=command.key_metrics or {},
            risks=command.risks or [],
            created_by=command.created_by,
        )

        saved = self._memo_repo.save(memo)
        if not saved:
            return MemoResult(
                success=False,
                message="Duplicate memo for this decision",
            )

        event = MemoCreatedEvent(
            event_id=str(uuid.uuid4()),
            memo_id=memo_id,
            decision_id=command.decision_id,
            ticker=command.ticker,
            decision=command.decision,
            conviction_level=command.conviction_level,
            created_at=datetime.utcnow().isoformat(),
        )

        return MemoResult(
            success=True,
            message="Memo created",
            memo_id=memo_id,
            events=[event],
        )

    def activate_memo(self, memo_id: str) -> MemoResult:
        """Activate a memo (DRAFT → ACTIVE)."""
        memo = self._memo_repo.get_by_id(memo_id)
        if memo is None:
            return MemoResult(success=False, message="Memo not found")

        try:
            memo.transition_to(MemoStatus.ACTIVE.value)
        except MemoStateError as e:
            return MemoResult(success=False, message=str(e))

        self._memo_repo.save(memo)

        event = MemoActivatedEvent(
            event_id=str(uuid.uuid4()),
            memo_id=memo_id,
            activated_at=datetime.utcnow().isoformat(),
        )

        return MemoResult(
            success=True,
            message="Memo activated",
            memo_id=memo_id,
            events=[event],
        )

    def revise_memo(
        self,
        memo_id: str,
        thesis: str,
        conviction_level: str,
        revised_by: str,
        reason: str = "",
    ) -> MemoResult:
        """Revise a memo's thesis and conviction."""
        memo = self._memo_repo.get_by_id(memo_id)
        if memo is None:
            return MemoResult(success=False, message="Memo not found")

        if memo.is_terminal:
            return MemoResult(
                success=False,
                message=f"Cannot revise memo in state {memo.status}",
            )

        memo.add_revision(thesis, conviction_level, revised_by, reason)
        self._memo_repo.save(memo)

        event = MemoRevisedEvent(
            event_id=str(uuid.uuid4()),
            memo_id=memo_id,
            revision_number=memo.revision_count,
            revised_by=revised_by,
            revision_reason=reason,
            revised_at=datetime.utcnow().isoformat(),
        )

        return MemoResult(
            success=True,
            message="Memo revised",
            memo_id=memo_id,
            events=[event],
        )

    def close_position(self, command: ClosePositionCommand) -> MemoResult:
        """Close a memo position with realized return."""
        memo = self._memo_repo.get_by_id(command.memo_id)
        if memo is None:
            return MemoResult(success=False, message="Memo not found")

        exit_date = command.exit_date or date.today()
        exit_price = Decimal(str(command.exit_price))

        realized = RealizedReturn.compute(
            ticker=memo.ticker,
            entry_date=memo.created_at.date() if memo.entry_price else exit_date,
            entry_price=memo.entry_price or Decimal("0"),
            exit_date=exit_date,
            exit_price=exit_price,
            quantity=command.quantity,
            target_price=memo.exit_target,
            close_reason=command.close_reason,
        )

        try:
            memo.close_position(realized)
        except MemoStateError as e:
            return MemoResult(success=False, message=str(e))

        self._memo_repo.save(memo)

        event = MemoClosedEvent(
            event_id=str(uuid.uuid4()),
            memo_id=command.memo_id,
            close_reason=command.close_reason,
            realized_return_pct=realized.realized_return_pct,
            target_error_pct=realized.target_error_pct,
            closed_at=datetime.utcnow().isoformat(),
        )

        return MemoResult(
            success=True,
            message="Position closed",
            memo_id=command.memo_id,
            events=[event],
        )

    def invalidate_memo(
        self, memo_id: str, reason: str
    ) -> MemoResult:
        """Invalidate a memo (thesis broken)."""
        memo = self._memo_repo.get_by_id(memo_id)
        if memo is None:
            return MemoResult(success=False, message="Memo not found")

        try:
            memo.invalidate(reason)
        except MemoStateError as e:
            return MemoResult(success=False, message=str(e))

        self._memo_repo.save(memo)

        event = MemoInvalidatedEvent(
            event_id=str(uuid.uuid4()),
            memo_id=memo_id,
            invalidation_reason=reason,
            invalidated_at=datetime.utcnow().isoformat(),
        )

        return MemoResult(
            success=True,
            message="Memo invalidated",
            memo_id=memo_id,
            events=[event],
        )

    def get_memo(self, memo_id: str) -> Optional[InvestmentMemo]:
        """Get a memo by ID."""
        return self._memo_repo.get_by_id(memo_id)

    def get_by_ticker(self, ticker: str) -> List[InvestmentMemo]:
        """Get all memos for a ticker."""
        return self._memo_repo.get_by_ticker(ticker)
