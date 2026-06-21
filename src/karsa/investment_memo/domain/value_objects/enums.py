"""Investment Memo enums -- Sprint-15."""

from enum import Enum


class MemoStatus(str, Enum):
    """Lifecycle status for investment memos."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"  # Approved and tracking
    CLOSED = "CLOSED"  # Position closed, return recorded
    INVALIDATED = "INVALIDATED"  # Thesis broken


class MemoDecision(str, Enum):
    """Investment decision types."""

    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    PASS = "PASS"


class ConvictionLevel(str, Enum):
    """Conviction levels."""

    STRONG = "STRONG"
    MEDIUM = "MEDIUM"
    WEAK = "WEAK"


class CloseReason(str, Enum):
    """Reasons for closing a memo position."""

    TARGET_HIT = "TARGET_HIT"
    STOP_LOSS = "STOP_LOSS"
    THESIS_BROKEN = "THESIS_BROKEN"
    TIME_LIMIT = "TIME_LIMIT"
    REBALANCE = "REBALANCE"
    MANUAL = "MANUAL"
