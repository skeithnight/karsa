"""ReviewCycle aggregate — Sprint-07 Wave-1."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from karsa.review.domain.value_objects.review_verdict import ReviewType
from karsa.review.domain.value_objects.decision_snapshot import DecisionSnapshot
from karsa.review.domain.value_objects.schedule_policy import SchedulePolicy
from karsa.review.domain.value_objects.review_template import ReviewTemplate


class ImmutableLedgerEntry:
    """Base class for write-once immutable ledger entries."""
    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise AttributeError(f"Cannot modify '{name}' of an immutable ledger entry.")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        raise AttributeError("Cannot delete attribute of an immutable ledger entry.")


@dataclass
class ReviewCycle(ImmutableLedgerEntry):
    """Write-once ledger entry for review cycles.

    Created when a CIO Decision passes eligibility review.
    Contains full decision context (DecisionSnapshot) to prevent
    hindsight contamination.
    """
    cycle_id: str
    decision_id: str
    proposal_id: Optional[str]
    journal_ref: str
    review_type: ReviewType
    decision_snapshot: DecisionSnapshot
    schedule_policy: SchedulePolicy
    review_template: ReviewTemplate
    eligibility_event_ref: str
    created_at: datetime
    created_by: str

    def __post_init__(self):
        if not self.cycle_id or not self.cycle_id.strip():
            raise ValueError("cycle_id cannot be empty.")
        if not self.decision_id or not self.decision_id.strip():
            raise ValueError("decision_id cannot be empty.")
        if not self.journal_ref or not self.journal_ref.strip():
            raise ValueError("journal_ref cannot be empty.")
        if not self.eligibility_event_ref or not self.eligibility_event_ref.strip():
            raise ValueError("eligibility_event_ref cannot be empty.")
        if not self.created_by or not self.created_by.strip():
            raise ValueError("created_by cannot be empty.")

    @property
    def schedule_due_date(self) -> datetime:
        return self.schedule_policy.due_date
