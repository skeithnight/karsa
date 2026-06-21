"""Investment Workflow enums -- Sprint-13. ADR-140."""

from enum import Enum


class DecisionState(str, Enum):
    """States for investment decision workflow."""

    PROPOSED = "PROPOSED"
    ANALYZING = "ANALYZING"
    DEBATING = "DEBATING"
    DECIDING = "DECIDING"
    RISK_REVIEW = "RISK_REVIEW"
    COMMITTEE_REVIEW = "COMMITTEE_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVISED = "REVISED"
    SUSPENDED = "SUSPENDED"


class AnalystType(str, Enum):
    """Types of investment analyst agents."""

    FUNDAMENTAL = "FUNDAMENTAL"
    TECHNICAL = "TECHNICAL"
    SENTIMENT = "SENTIMENT"
    RISK = "RISK"
    MARKET = "MARKET"


class ConvictionLevel(str, Enum):
    """Conviction levels for investment decisions."""

    STRONG = "STRONG"
    MEDIUM = "MEDIUM"
    WEAK = "WEAK"


class DecisionType(str, Enum):
    """Investment decision types."""

    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    PASS = "PASS"


# Valid state transitions (ADR-140)
VALID_TRANSITIONS = {
    DecisionState.PROPOSED: {DecisionState.ANALYZING, DecisionState.REJECTED},
    DecisionState.ANALYZING: {DecisionState.DEBATING, DecisionState.REJECTED, DecisionState.SUSPENDED},
    DecisionState.DEBATING: {DecisionState.DECIDING, DecisionState.REJECTED, DecisionState.SUSPENDED},
    DecisionState.DECIDING: {DecisionState.RISK_REVIEW, DecisionState.REJECTED, DecisionState.REVISED, DecisionState.SUSPENDED},
    DecisionState.RISK_REVIEW: {DecisionState.COMMITTEE_REVIEW, DecisionState.REJECTED, DecisionState.REVISED, DecisionState.SUSPENDED},
    DecisionState.COMMITTEE_REVIEW: {DecisionState.APPROVED, DecisionState.REJECTED, DecisionState.REVISED, DecisionState.SUSPENDED},
    DecisionState.REVISED: {DecisionState.ANALYZING},
    DecisionState.SUSPENDED: {DecisionState.ANALYZING, DecisionState.DEBATING, DecisionState.DECIDING, DecisionState.REJECTED},
    DecisionState.APPROVED: set(),  # terminal
    DecisionState.REJECTED: set(),  # terminal
}
