from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List

@dataclass(frozen=True)
class PortfolioDecisionMadeEvent:
    event_id: str
    event_type: str
    correlation_id: str
    causation_id: str
    decision_id: str
    portfolio_id: str
    actor: Dict[str, Any]  # {"actor_id": "...", "actor_type": "HUMAN"|"AGENT"}
    action_type: str  # "APPROVE_ALLOCATION", "REJECT_ALLOCATION", "OVERRIDE"
    payload: Dict[str, Any]
    rationale: Dict[str, Any]  # {"summary": "...", "references": ["..."]}
    cryptographic_signature: Dict[str, Any]  # {"key_id": "...", "algorithm": "...", "signature_hex": "..."}
    timestamp: datetime
    event_version: int = 1

    def __post_init__(self):
        if not self.event_id or not self.event_id.strip():
            raise ValueError("event_id cannot be empty.")
        if not self.event_type or not self.event_type.strip():
            raise ValueError("event_type cannot be empty.")
        if not self.correlation_id or not self.correlation_id.strip():
            raise ValueError("correlation_id cannot be empty.")
        if not self.causation_id or not self.causation_id.strip():
            raise ValueError("causation_id cannot be empty.")
        if not self.decision_id or not self.decision_id.strip():
            raise ValueError("decision_id cannot be empty.")
        if not self.portfolio_id or not self.portfolio_id.strip():
            raise ValueError("portfolio_id cannot be empty.")
        if "actor_id" not in self.actor or "actor_type" not in self.actor:
            raise ValueError("actor must contain actor_id and actor_type.")
        if self.actor["actor_type"] not in ("HUMAN", "AGENT"):
            raise ValueError("actor_type must be either HUMAN or AGENT.")
        if not self.action_type or not self.action_type.strip():
            raise ValueError("action_type cannot be empty.")
        if "key_id" not in self.cryptographic_signature or "signature_hex" not in self.cryptographic_signature:
            raise ValueError("cryptographic_signature must contain key_id and signature_hex.")


# --- Sprint-06 Proposal CIO Events ---

@dataclass(frozen=True)
class AllocationProposalApprovedEvent:
    """Emitted when CIO approves an allocation proposal."""
    event_id: str
    proposal_id: str
    decision_id: str
    approved_by: str
    approved_at: datetime
    event_sequence: int = 0
    event_type: str = "AllocationProposalApprovedEvent"
    event_version: int = 1

    def __post_init__(self):
        if not self.proposal_id:
            raise ValueError("proposal_id cannot be empty.")
        if not self.decision_id:
            raise ValueError("decision_id cannot be empty.")


@dataclass(frozen=True)
class AllocationProposalRejectedEvent:
    """Emitted when CIO rejects an allocation proposal."""
    event_id: str
    proposal_id: str
    decision_id: str
    rejected_by: str
    rejection_reason: str
    rejected_at: datetime
    event_sequence: int = 0
    event_type: str = "AllocationProposalRejectedEvent"
    event_version: int = 1

    def __post_init__(self):
        if not self.proposal_id:
            raise ValueError("proposal_id cannot be empty.")
        if not self.decision_id:
            raise ValueError("decision_id cannot be empty.")


@dataclass(frozen=True)
class AllocationProposalModifiedEvent:
    """Emitted when CIO modifies an allocation proposal."""
    event_id: str
    original_proposal_id: str
    decision_id: str
    modified_weights: Dict[str, float]
    modification_reason: str
    modified_by: str
    modified_at: datetime
    event_sequence: int = 0
    event_type: str = "AllocationProposalModifiedEvent"
    event_version: int = 1

    def __post_init__(self):
        if not self.original_proposal_id:
            raise ValueError("original_proposal_id cannot be empty.")
        if not self.decision_id:
            raise ValueError("decision_id cannot be empty.")
