from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from karsa.cio.exceptions import ImmutabilityViolationException
from karsa.cio.value_objects import CommitteeVote, OverrideReason

class ImmutableAggregate:
    """Base class for strictly immutable aggregates that prevent property modification at runtime."""
    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise ImmutabilityViolationException("Cannot modify property of an immutable aggregate.")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        raise ImmutabilityViolationException("Cannot delete property of an immutable aggregate.")

@dataclass
class CIODecisionAggregate(ImmutableAggregate):
    decision_id: str
    calculation_id: Optional[str]
    governance_exception_id: Optional[str]
    decision_journal_ref: str
    portfolio_snapshot_hash: str
    action_type: str  # "APPROVE_ALLOCATION", "REJECT_ALLOCATION", "OVERRIDE"
    target_node_type: str  # "PORTFOLIO", "STRATEGY", "THESIS", "WORKER"
    target_node_id: str
    decision_payload: Dict[str, Any]
    cryptographic_signature: str
    created_at: datetime
    votes: List[CommitteeVote]
    override_reason: Optional[OverrideReason] = None

    def __post_init__(self):
        if not self.decision_id or not self.decision_id.strip():
            raise ValueError("decision_id cannot be empty.")
        if not self.decision_journal_ref or not self.decision_journal_ref.strip():
            raise ValueError("decision_journal_ref cannot be empty.")
        if not self.portfolio_snapshot_hash or not self.portfolio_snapshot_hash.strip():
            raise ValueError("portfolio_snapshot_hash cannot be empty.")
        if self.action_type not in ("APPROVE_ALLOCATION", "REJECT_ALLOCATION", "OVERRIDE"):
            raise ValueError("Invalid action_type.")
        if self.target_node_type not in ("PORTFOLIO", "STRATEGY", "THESIS", "WORKER"):
            raise ValueError("Invalid target_node_type.")
        if not self.target_node_id or not self.target_node_id.strip():
            raise ValueError("target_node_id cannot be empty.")
        if not self.cryptographic_signature or not self.cryptographic_signature.strip():
            raise ValueError("cryptographic_signature cannot be empty.")
        
        # Enforce that overrides must have a justification/reason
        if self.action_type == "OVERRIDE" and not self.override_reason:
            raise ValueError("An override decision must contain an override_reason.")
