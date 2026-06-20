"""ProposalStatusProjectionService — Sprint-06 Wave-6.

Consumes allocation proposal events and updates the ProposalStatusProjection
read-side model. No business logic. Projection only.
"""
from typing import Dict, Any

from karsa.allocation.domain.repository.proposal_status_projection_repository import ProposalStatusProjectionRepository


class ProposalStatusProjectionService:
    """Event-driven projection service for proposal status lifecycle.

    Responsibilities:
    - Consume proposal lifecycle events
    - Update proposal_status_projection table
    - Enforce event_sequence ordering (handled by repository)

    No business logic. Pure projection.
    """

    def __init__(self, projection_repo: ProposalStatusProjectionRepository):
        self.projection_repo = projection_repo

    def handle_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Dispatches an event to the appropriate handler.

        Args:
            event_type: The event type string.
            payload: The event payload as a dict.
        """
        handlers = {
            "AllocationProposalGeneratedEvent": self.upsert_pending,
            "AllocationProposalApprovedEvent": self.mark_approved,
            "AllocationProposalRejectedEvent": self.mark_rejected,
            "AllocationProposalModifiedEvent": self.mark_modified,
            "AllocationProposalExpiredEvent": self.mark_expired,
        }
        handler = handlers.get(event_type)
        if handler:
            handler(payload)

    def upsert_pending(self, payload: Dict[str, Any]) -> None:
        """Handles AllocationProposalGeneratedEvent.

        Creates a PENDING status row. ON CONFLICT DO NOTHING ensures idempotency.
        """
        proposal_id = payload.get("proposal_id", "")
        event_sequence = payload.get("event_sequence", 0)
        if not proposal_id:
            return
        self.projection_repo.upsert_pending(proposal_id, event_sequence)

    def mark_approved(self, payload: Dict[str, Any]) -> None:
        """Handles AllocationProposalApprovedEvent.

        Updates status to APPROVED. event_sequence guard prevents out-of-order updates.
        """
        proposal_id = payload.get("proposal_id", "")
        decision_id = payload.get("decision_id", "")
        approved_by = payload.get("approved_by", "")
        approved_at = payload.get("approved_at", "")
        event_sequence = payload.get("event_sequence", 0)
        if not proposal_id or not decision_id:
            return
        self.projection_repo.mark_approved(
            proposal_id, decision_id, approved_by, approved_at, event_sequence
        )

    def mark_rejected(self, payload: Dict[str, Any]) -> None:
        """Handles AllocationProposalRejectedEvent.

        Updates status to REJECTED. event_sequence guard prevents out-of-order updates.
        """
        proposal_id = payload.get("proposal_id", "")
        decision_id = payload.get("decision_id", "")
        rejected_by = payload.get("rejected_by", "")
        rejected_at = payload.get("rejected_at", "")
        event_sequence = payload.get("event_sequence", 0)
        if not proposal_id or not decision_id:
            return
        self.projection_repo.mark_rejected(
            proposal_id, decision_id, rejected_by, rejected_at, event_sequence
        )

    def mark_modified(self, payload: Dict[str, Any]) -> None:
        """Handles AllocationProposalModifiedEvent.

        Updates status to MODIFIED. event_sequence guard prevents out-of-order updates.
        """
        proposal_id = payload.get("original_proposal_id", "")
        decision_id = payload.get("decision_id", "")
        modified_by = payload.get("modified_by", "")
        modified_at = payload.get("modified_at", "")
        event_sequence = payload.get("event_sequence", 0)
        if not proposal_id or not decision_id:
            return
        self.projection_repo.mark_modified(
            proposal_id, decision_id, modified_by, modified_at, event_sequence
        )

    def mark_expired(self, payload: Dict[str, Any]) -> None:
        """Handles AllocationProposalExpiredEvent.

        Updates status to EXPIRED. event_sequence guard prevents out-of-order updates.
        """
        proposal_id = payload.get("proposal_id", "")
        expired_at = payload.get("expired_at", "")
        event_sequence = payload.get("event_sequence", 0)
        if not proposal_id:
            return
        self.projection_repo.mark_expired(proposal_id, expired_at, event_sequence)
