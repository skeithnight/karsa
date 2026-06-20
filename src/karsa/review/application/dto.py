"""Command and Response DTOs for Review Engine Application Services — Sprint-07 Wave-3."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional


# --- Command DTOs ---

@dataclass(frozen=True)
class ScheduleReviewCommand:
    """Command to schedule a new review cycle."""
    decision_id: str
    proposal_id: Optional[str]
    journal_ref: str
    review_type: str
    decision_snapshot: Dict[str, Any]
    schedule_policy: Dict[str, Any]
    review_template: Dict[str, Any]
    eligibility_event_ref: str
    created_by: str


@dataclass(frozen=True)
class ExecuteReviewCommand:
    """Command to execute a review against actual outcomes."""
    cycle_id: str
    actual_outcome: Dict[str, Any]
    executed_by: str
    rationale: str


@dataclass(frozen=True)
class ApplyCapabilityAdjustmentCommand:
    """Command to apply capability score adjustments from a review."""
    review_id: str
    target_urn: str
    target_type: str
    contribution_bps: float


@dataclass(frozen=True)
class RebuildProjectionCommand:
    """Command to rebuild a projection from scratch."""
    projection_name: str  # capability_score | review_coverage | cycle_status


@dataclass(frozen=True)
class PublishOutboxCommand:
    """Command to publish pending outbox events."""
    batch_size: int = 100
    max_retries: int = 3


# --- Response DTOs ---

@dataclass(frozen=True)
class ScheduleReviewResponse:
    """Response from scheduling a review cycle."""
    cycle_id: str
    decision_id: str
    review_type: str
    due_date: str
    created_at: str


@dataclass(frozen=True)
class ExecuteReviewResponse:
    """Response from executing a review."""
    review_id: str
    cycle_id: str
    verdict: str
    executed_at: str
    attribution_count: int
    adjustment_count: int


@dataclass(frozen=True)
class ApplyCapabilityAdjustmentResponse:
    """Response from applying a capability adjustment."""
    adjustment_id: str
    target_urn: str
    score_delta: float
    confidence_delta: float


@dataclass(frozen=True)
class RebuildProjectionResponse:
    """Response from rebuilding a projection."""
    projection_name: str
    rows_affected: int
    rebuilt_at: str


@dataclass(frozen=True)
class PublishOutboxResponse:
    """Response from publishing outbox events."""
    published_count: int
    failed_count: int
    published_at: str
