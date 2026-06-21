"""Investment Workflow domain events -- Sprint-13. ADR-140.

All events are frozen dataclasses following the capability_engine convention.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class InvestmentDecisionProposedEvent:
    """Published when an investment decision is initiated."""

    event_id: str
    decision_id: str  # URN
    capability_family_id: str
    ticker: str
    proposed_by: str = ""
    proposed_at: str = ""

    event_sequence: int = 0
    event_type: str = "InvestmentDecisionProposedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "decision_id": self.decision_id,
            "capability_family_id": self.capability_family_id,
            "ticker": self.ticker,
            "proposed_by": self.proposed_by,
            "proposed_at": self.proposed_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class AnalystOutputRecordedEvent:
    """Published when an analyst agent completes analysis."""

    event_id: str
    decision_id: str
    analyst_type: str  # AnalystType value
    score: float  # 0.0-10.0
    confidence: float  # 0.0-1.0
    recorded_at: str = ""

    event_sequence: int = 0
    event_type: str = "AnalystOutputRecordedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "decision_id": self.decision_id,
            "analyst_type": self.analyst_type,
            "score": self.score,
            "confidence": self.confidence,
            "recorded_at": self.recorded_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class DebateCompletedEvent:
    """Published when bull/bear debate finishes."""

    event_id: str
    decision_id: str
    round_count: int
    bull_conviction_level: str
    bear_conviction_level: str
    completed_at: str = ""

    event_sequence: int = 0
    event_type: str = "DebateCompletedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "decision_id": self.decision_id,
            "round_count": self.round_count,
            "bull_conviction_level": self.bull_conviction_level,
            "bear_conviction_level": self.bear_conviction_level,
            "completed_at": self.completed_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class DecisionMemoCreatedEvent:
    """Published when Portfolio Manager creates investment memo."""

    event_id: str
    decision_id: str
    ticker: str
    decision: str  # DecisionType value
    conviction_level: str
    entry_price: Optional[str] = None
    exit_target: Optional[str] = None
    created_at: str = ""

    event_sequence: int = 0
    event_type: str = "DecisionMemoCreatedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "decision_id": self.decision_id,
            "ticker": self.ticker,
            "decision": self.decision,
            "conviction_level": self.conviction_level,
            "entry_price": self.entry_price,
            "exit_target": self.exit_target,
            "created_at": self.created_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class RiskVetoIssuedEvent:
    """Published when Risk Officer rejects or requests revision."""

    event_id: str
    decision_id: str
    veto_reason: str
    suggestion: str = ""
    issued_at: str = ""

    event_sequence: int = 0
    event_type: str = "RiskVetoIssuedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "decision_id": self.decision_id,
            "veto_reason": self.veto_reason,
            "suggestion": self.suggestion,
            "issued_at": self.issued_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class DecisionApprovedEvent:
    """Published when Committee Chair approves decision."""

    event_id: str
    decision_id: str
    approved_by: str
    approved_at: str = ""

    event_sequence: int = 0
    event_type: str = "DecisionApprovedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "decision_id": self.decision_id,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class DecisionRejectedEvent:
    """Published when decision is rejected."""

    event_id: str
    decision_id: str
    rejected_by: str
    rejection_reason: str = ""
    rejected_at: str = ""

    event_sequence: int = 0
    event_type: str = "DecisionRejectedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "decision_id": self.decision_id,
            "rejected_by": self.rejected_by,
            "rejection_reason": self.rejection_reason,
            "rejected_at": self.rejected_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class DecisionRevisedEvent:
    """Published when decision is sent back for re-analysis."""

    event_id: str
    decision_id: str
    revision_reason: str
    revised_at: str = ""

    event_sequence: int = 0
    event_type: str = "DecisionRevisedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "decision_id": self.decision_id,
            "revision_reason": self.revision_reason,
            "revised_at": self.revised_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }
