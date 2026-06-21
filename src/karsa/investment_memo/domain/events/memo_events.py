"""Investment Memo domain events -- Sprint-15.

All events are frozen dataclasses.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class MemoCreatedEvent:
    """Published when an investment memo is created."""

    event_id: str
    memo_id: str
    decision_id: str
    ticker: str
    decision: str
    conviction_level: str
    created_at: str = ""

    event_sequence: int = 0
    event_type: str = "MemoCreatedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "memo_id": self.memo_id,
            "decision_id": self.decision_id,
            "ticker": self.ticker,
            "decision": self.decision,
            "conviction_level": self.conviction_level,
            "created_at": self.created_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class MemoActivatedEvent:
    """Published when a memo transitions to ACTIVE."""

    event_id: str
    memo_id: str
    activated_at: str = ""

    event_sequence: int = 0
    event_type: str = "MemoActivatedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "memo_id": self.memo_id,
            "activated_at": self.activated_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class MemoRevisedEvent:
    """Published when a memo is revised."""

    event_id: str
    memo_id: str
    revision_number: int
    revised_by: str
    revision_reason: str = ""
    revised_at: str = ""

    event_sequence: int = 0
    event_type: str = "MemoRevisedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "memo_id": self.memo_id,
            "revision_number": self.revision_number,
            "revised_by": self.revised_by,
            "revision_reason": self.revision_reason,
            "revised_at": self.revised_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class MemoClosedEvent:
    """Published when a memo position is closed."""

    event_id: str
    memo_id: str
    close_reason: str
    realized_return_pct: float
    target_error_pct: Optional[float] = None
    closed_at: str = ""

    event_sequence: int = 0
    event_type: str = "MemoClosedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "memo_id": self.memo_id,
            "close_reason": self.close_reason,
            "realized_return_pct": self.realized_return_pct,
            "target_error_pct": self.target_error_pct,
            "closed_at": self.closed_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class MemoInvalidatedEvent:
    """Published when a memo's thesis is broken."""

    event_id: str
    memo_id: str
    invalidation_reason: str
    invalidated_at: str = ""

    event_sequence: int = 0
    event_type: str = "MemoInvalidatedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "memo_id": self.memo_id,
            "invalidation_reason": self.invalidation_reason,
            "invalidated_at": self.invalidated_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }
