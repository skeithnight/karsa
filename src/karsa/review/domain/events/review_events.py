"""Review Engine domain events — Sprint-07 Wave-1."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional


@dataclass(frozen=True)
class ReviewEligibilityEvaluatedEvent:
    """Emitted for every PortfolioDecisionMadeEvent.

    Records eligibility decision as immutable historical fact.
    Replay never re-evaluates — event is authoritative.
    """
    event_id: str
    evaluation_id: str
    decision_id: str
    eligible: bool
    review_type: Optional[str]
    strategy_name: str
    strategy_version: str
    evaluation_reason: str
    evaluated_at: datetime
    event_sequence: int = 0
    event_type: str = "ReviewEligibilityEvaluatedEvent"
    event_version: int = 1

    def __post_init__(self):
        if not self.evaluation_id:
            raise ValueError("evaluation_id cannot be empty.")
        if not self.decision_id:
            raise ValueError("decision_id cannot be empty.")
        if not self.strategy_name:
            raise ValueError("strategy_name cannot be empty.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "evaluation_id": self.evaluation_id,
            "decision_id": self.decision_id,
            "eligible": self.eligible,
            "review_type": self.review_type,
            "strategy_name": self.strategy_name,
            "strategy_version": self.strategy_version,
            "evaluation_reason": self.evaluation_reason,
            "evaluated_at": self.evaluated_at.isoformat(),
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
        }


@dataclass(frozen=True)
class ReviewCycleCreatedEvent:
    """Emitted when a new review cycle is created."""
    event_id: str
    cycle_id: str
    decision_id: str
    proposal_id: Optional[str]
    journal_ref: str
    review_type: str
    decision_snapshot: Dict[str, Any]
    schedule_policy: Dict[str, Any]
    review_template: Dict[str, Any]
    eligibility_event_ref: str
    created_by: str
    created_at: datetime
    event_sequence: int = 0
    event_type: str = "ReviewCycleCreatedEvent"
    event_version: int = 1

    def __post_init__(self):
        if not self.cycle_id:
            raise ValueError("cycle_id cannot be empty.")
        if not self.decision_id:
            raise ValueError("decision_id cannot be empty.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "cycle_id": self.cycle_id,
            "decision_id": self.decision_id,
            "proposal_id": self.proposal_id,
            "journal_ref": self.journal_ref,
            "review_type": self.review_type,
            "decision_snapshot": self.decision_snapshot,
            "schedule_policy": self.schedule_policy,
            "review_template": self.review_template,
            "eligibility_event_ref": self.eligibility_event_ref,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
        }


@dataclass(frozen=True)
class ReviewDueEvent:
    """Emitted when a review approaches its due date."""
    event_id: str
    cycle_id: str
    review_due_date: datetime
    days_until_due: int
    created_at: datetime
    event_sequence: int = 0
    event_type: str = "ReviewDueEvent"
    event_version: int = 1

    def __post_init__(self):
        if not self.cycle_id:
            raise ValueError("cycle_id cannot be empty.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "cycle_id": self.cycle_id,
            "review_due_date": self.review_due_date.isoformat(),
            "days_until_due": self.days_until_due,
            "created_at": self.created_at.isoformat(),
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
        }


@dataclass(frozen=True)
class ReviewOverdueEvent:
    """Emitted when a review passes its overdue threshold."""
    event_id: str
    cycle_id: str
    days_overdue: int
    original_due_date: datetime
    detected_at: datetime
    event_sequence: int = 0
    event_type: str = "ReviewOverdueEvent"
    event_version: int = 1

    def __post_init__(self):
        if not self.cycle_id:
            raise ValueError("cycle_id cannot be empty.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "cycle_id": self.cycle_id,
            "days_overdue": self.days_overdue,
            "original_due_date": self.original_due_date.isoformat(),
            "detected_at": self.detected_at.isoformat(),
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
        }


@dataclass(frozen=True)
class ReviewExecutedEvent:
    """Emitted when a review is executed against actual outcomes."""
    event_id: str
    review_id: str
    cycle_id: str
    review_type: str
    actual_outcome: Dict[str, Any]
    variance: Dict[str, Any]
    verdict: str
    rationale: str
    executed_by: str
    executed_at: datetime
    event_sequence: int = 0
    event_type: str = "ReviewExecutedEvent"
    event_version: int = 1

    def __post_init__(self):
        if not self.review_id:
            raise ValueError("review_id cannot be empty.")
        if not self.cycle_id:
            raise ValueError("cycle_id cannot be empty.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "review_id": self.review_id,
            "cycle_id": self.cycle_id,
            "review_type": self.review_type,
            "actual_outcome": self.actual_outcome,
            "variance": self.variance,
            "verdict": self.verdict,
            "rationale": self.rationale,
            "executed_by": self.executed_by,
            "executed_at": self.executed_at.isoformat(),
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
        }


@dataclass(frozen=True)
class AttributionGeneratedEvent:
    """Emitted for each attribution entry created during review execution."""
    event_id: str
    attribution_id: str
    review_id: str
    dimension: str
    target_urn: str
    contribution_bps: float
    contribution_pct: float
    attribution_type: str
    evidence: Dict[str, Any]
    created_at: datetime
    event_sequence: int = 0
    event_type: str = "AttributionGeneratedEvent"
    event_version: int = 1

    def __post_init__(self):
        if not self.attribution_id:
            raise ValueError("attribution_id cannot be empty.")
        if not self.review_id:
            raise ValueError("review_id cannot be empty.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "attribution_id": self.attribution_id,
            "review_id": self.review_id,
            "dimension": self.dimension,
            "target_urn": self.target_urn,
            "contribution_bps": self.contribution_bps,
            "contribution_pct": self.contribution_pct,
            "attribution_type": self.attribution_type,
            "evidence": self.evidence,
            "created_at": self.created_at.isoformat(),
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
        }


@dataclass(frozen=True)
class CapabilityScoreAdjustmentCreatedEvent:
    """Emitted for each capability score adjustment created during review execution."""
    event_id: str
    adjustment_id: str
    target_urn: str
    target_type: str
    score_delta: float
    confidence_delta: float
    review_id: str
    rationale: str
    created_at: datetime
    event_sequence: int = 0
    event_type: str = "CapabilityScoreAdjustmentCreatedEvent"
    event_version: int = 1

    def __post_init__(self):
        if not self.adjustment_id:
            raise ValueError("adjustment_id cannot be empty.")
        if not self.target_urn:
            raise ValueError("target_urn cannot be empty.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "adjustment_id": self.adjustment_id,
            "target_urn": self.target_urn,
            "target_type": self.target_type,
            "score_delta": self.score_delta,
            "confidence_delta": self.confidence_delta,
            "review_id": self.review_id,
            "rationale": self.rationale,
            "created_at": self.created_at.isoformat(),
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
        }
