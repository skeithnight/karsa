from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from karsa.cio.exceptions import ImmutabilityViolationException
from karsa.allocation.domain.model.value_objects import (
    ProposedWeight, PolicySnapshot, PortfolioContext
)


class ImmutableLedgerEntry:
    """Base class for write-once immutable ledger entries."""
    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise ImmutabilityViolationException(
                f"Cannot modify property '{name}' of an immutable ledger entry."
            )
        super().__setattr__(name, value)

    def __delattr__(self, name):
        raise ImmutabilityViolationException(
            "Cannot delete property of an immutable ledger entry."
        )


@dataclass
class AllocationProposal(ImmutableLedgerEntry):
    """Write-once immutable ledger entry for allocation proposals.

    Status is NOT stored on this aggregate. Status is derived from events
    via the ProposalStatusProjection read-side projection.
    """
    proposal_id: str
    policy_id: str
    policy_snapshot: PolicySnapshot
    journal_ref: str
    proposed_weights: Dict[str, ProposedWeight]
    total_capital: float
    proposal_rationale: str
    portfolio_context: PortfolioContext
    context_hash: str
    generated_at: datetime

    def __post_init__(self):
        if not self.proposal_id or not self.proposal_id.strip():
            raise ValueError("proposal_id cannot be empty.")
        if not self.policy_id or not self.policy_id.strip():
            raise ValueError("policy_id cannot be empty.")
        if not self.journal_ref or not self.journal_ref.strip():
            raise ValueError("journal_ref cannot be empty.")
        if not self.proposed_weights:
            raise ValueError("proposed_weights cannot be empty.")
        if self.total_capital < 0:
            raise ValueError("total_capital cannot be negative.")
        if not self.proposal_rationale or not self.proposal_rationale.strip():
            raise ValueError("proposal_rationale cannot be empty.")
        if not self.context_hash or not self.context_hash.strip():
            raise ValueError("context_hash cannot be empty.")

        # Validate weights sum to <= 1.0
        total_weight = sum(w.proposed_weight for w in self.proposed_weights.values())
        if total_weight > 1.0 + 1e-9:
            raise ValueError(
                f"Proposed weights sum to {total_weight}, which exceeds 1.0."
            )
