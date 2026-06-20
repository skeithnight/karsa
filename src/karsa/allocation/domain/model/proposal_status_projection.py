from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class ProposalStatusProjection:
    """Read-side projection derived from proposal lifecycle events.

    This is NOT a domain aggregate. It is a derived read model.
    Status is computed from events, not stored on the AllocationProposal aggregate.
    """
    proposal_id: str
    status: str  # PENDING | APPROVED | REJECTED | MODIFIED | EXPIRED
    decision_id: Optional[str] = None
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None
    event_sequence: int = 0

    def __post_init__(self):
        if not self.proposal_id or not self.proposal_id.strip():
            raise ValueError("proposal_id cannot be empty.")
        valid_statuses = ("PENDING", "APPROVED", "REJECTED", "MODIFIED", "EXPIRED")
        if self.status not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got '{self.status}'.")
