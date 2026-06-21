"""InvestmentMemo aggregate -- Sprint-15.

Lifecycle tracking for investment memos with realized return feedback.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from karsa.investment_memo.domain.entities.memo_revision import MemoRevision
from karsa.investment_memo.domain.exceptions import (
    DuplicateMemoError,
    InvalidMemoError,
    MemoStateError,
)
from karsa.investment_memo.domain.value_objects.enums import (
    CloseReason,
    ConvictionLevel,
    MemoDecision,
    MemoStatus,
)
from karsa.investment_memo.domain.value_objects.realized_return import (
    RealizedReturn,
)

# Valid state transitions
VALID_TRANSITIONS = {
    MemoStatus.DRAFT: {MemoStatus.ACTIVE, MemoStatus.INVALIDATED},
    MemoStatus.ACTIVE: {MemoStatus.CLOSED, MemoStatus.INVALIDATED},
    MemoStatus.CLOSED: set(),  # terminal
    MemoStatus.INVALIDATED: set(),  # terminal
}


class ImmutableLedgerEntry:
    """Write-once base class."""

    def __setattr__(self, name: str, value: object) -> None:
        if "_initialized" in self.__dict__ and self._initialized:
            raise AttributeError(
                f"Cannot set attribute '{name}' on immutable ledger entry"
            )
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError(
            f"Cannot delete attribute '{name}' on immutable ledger entry"
        )


@dataclass
class InvestmentMemo(ImmutableLedgerEntry):
    """Aggregate for investment memo lifecycle.

    States: DRAFT → ACTIVE → CLOSED | INVALIDATED

    Tracks:
    - Investment thesis and conviction
    - Entry/exit price targets
    - Revision history
    - Realized return (when position closes)
    - Target accuracy feedback loop
    """

    # Identity
    memo_id: str  # URN
    decision_id: str  # Links to investment_workflow decision
    ticker: str

    # Decision
    decision: str  # MemoDecision value
    conviction_level: str  # ConvictionLevel value
    conviction_score: float = 0.0  # 0.0-10.0

    # Thesis
    thesis: str = ""
    key_metrics: dict = field(default_factory=dict)
    risks: List[str] = field(default_factory=list)

    # Price targets
    entry_price: Optional[Decimal] = None
    exit_target: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    position_size_pct: Optional[float] = None

    # Lifecycle
    status: str = MemoStatus.DRAFT.value
    revisions: List[MemoRevision] = field(default_factory=list)

    # Realized return (populated when CLOSED)
    realized_return: Optional[RealizedReturn] = None

    # Metadata
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        self._initialized = True
        self._validate()

    def _validate(self) -> None:
        if not self.memo_id:
            raise InvalidMemoError("memo_id is required")
        if not self.decision_id:
            raise InvalidMemoError("decision_id is required")
        if not self.ticker:
            raise InvalidMemoError("ticker is required")
        if not self.decision:
            raise InvalidMemoError("decision is required")
        valid_decisions = {e.value for e in MemoDecision}
        if self.decision not in valid_decisions:
            raise InvalidMemoError(
                f"decision must be one of {valid_decisions}"
            )
        valid_convictions = {e.value for e in ConvictionLevel}
        if self.conviction_level not in valid_convictions:
            raise InvalidMemoError(
                f"conviction_level must be one of {valid_convictions}"
            )
        if not 0.0 <= self.conviction_score <= 10.0:
            raise InvalidMemoError(
                f"conviction_score must be 0.0-10.0"
            )

    def can_transition_to(self, new_status: str) -> bool:
        current = MemoStatus(self.status)
        target = MemoStatus(new_status)
        return target in VALID_TRANSITIONS.get(current, set())

    def transition_to(self, new_status: str) -> None:
        if not self.can_transition_to(new_status):
            raise MemoStateError(
                f"Cannot transition from {self.status} to {new_status}"
            )
        object.__setattr__(self, "status", new_status)
        object.__setattr__(self, "updated_at", datetime.utcnow())

    def add_revision(
        self, thesis: str, conviction_level: str,
        revised_by: str, reason: str = "",
    ) -> None:
        """Add a revision to the memo."""
        revision = MemoRevision(
            revision_number=len(self.revisions) + 1,
            thesis=thesis,
            conviction_level=conviction_level,
            revised_by=revised_by,
            revision_reason=reason,
        )
        self.revisions.append(revision)
        object.__setattr__(self, "thesis", thesis)
        object.__setattr__(self, "conviction_level", conviction_level)
        object.__setattr__(self, "updated_at", datetime.utcnow())

    def close_position(self, realized_return: RealizedReturn) -> None:
        """Close the memo position with realized return."""
        if self.status != MemoStatus.ACTIVE.value:
            raise MemoStateError(
                f"Cannot close memo in state {self.status}"
            )
        object.__setattr__(self, "realized_return", realized_return)
        self.transition_to(MemoStatus.CLOSED.value)

    def invalidate(self, reason: str) -> None:
        """Invalidate the memo (thesis broken)."""
        if self.status in {
            MemoStatus.CLOSED.value,
            MemoStatus.INVALIDATED.value,
        }:
            raise MemoStateError(
                f"Cannot invalidate memo in state {self.status}"
            )
        self.transition_to(MemoStatus.INVALIDATED.value)

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            MemoStatus.CLOSED.value,
            MemoStatus.INVALIDATED.value,
        }

    @property
    def revision_count(self) -> int:
        return len(self.revisions)

    @property
    def has_realized_return(self) -> bool:
        return self.realized_return is not None

    @property
    def target_accuracy(self) -> Optional[float]:
        """Target accuracy if realized return exists."""
        if self.realized_return and self.realized_return.target_error_pct is not None:
            return 100.0 - self.realized_return.target_error_pct
        return None
