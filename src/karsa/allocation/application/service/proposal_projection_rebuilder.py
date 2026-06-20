"""ProposalProjectionRebuilder — Sprint-06 Wave-6.

Handles deterministic rebuild of the proposal_status_projection table
from the event journal.
"""
from typing import List, Dict, Any, Callable, Optional

from karsa.allocation.domain.model.proposal_status_projection import ProposalStatusProjection
from karsa.allocation.domain.repository.proposal_status_projection_repository import ProposalStatusProjectionRepository
from karsa.allocation.application.service.proposal_status_projection_service import ProposalStatusProjectionService


class ProposalProjectionRebuilder:
    """Rebuilds proposal_status_projection from event journal.

    Usage:
        rebuilder = ProposalProjectionRebuilder(projection_repo, projection_service)
        rebuilder.reset_projection()
        rebuilder.rebuild(events)
        assert rebuilder.verify_rebuild()
    """

    # Event types that affect proposal status
    PROPOSAL_EVENT_TYPES = {
        "AllocationProposalGeneratedEvent",
        "AllocationProposalApprovedEvent",
        "AllocationProposalRejectedEvent",
        "AllocationProposalModifiedEvent",
        "AllocationProposalExpiredEvent",
    }

    def __init__(
        self,
        projection_repo: ProposalStatusProjectionRepository,
        projection_service: ProposalStatusProjectionService,
        truncate_fn: Optional[Callable[[], None]] = None,
    ):
        self.projection_repo = projection_repo
        self.projection_service = projection_service
        self.truncate_fn = truncate_fn

    def reset_projection(self) -> None:
        """Clears the projection table for rebuild.

        If truncate_fn is provided (Postgres TRUNCATE), uses that.
        Otherwise clears via in-memory repository.
        """
        if self.truncate_fn:
            self.truncate_fn()
        else:
            # In-memory fallback: remove all projections
            all_projections = self.projection_repo.list_all(limit=10000)
            for proj in all_projections:
                # In-memory repos support direct deletion
                if hasattr(self.projection_repo, '_projections'):
                    self.projection_repo._projections.pop(proj.proposal_id, None)

    def rebuild(self, events: List[Dict[str, Any]]) -> int:
        """Replays events to rebuild projection state.

        Args:
            events: List of event dicts from the journal. Each must have
                    'event_type' and 'payload' keys.

        Returns:
            Number of proposal events processed.
        """
        processed = 0
        for event in events:
            event_type = event.get("event_type", "")
            if event_type in self.PROPOSAL_EVENT_TYPES:
                payload = event.get("payload", {})
                # Ensure event_sequence is in payload for idempotency
                if "event_sequence" not in payload:
                    payload["event_sequence"] = event.get("global_sequence", 0)
                self.projection_service.handle_event(event_type, payload)
                processed += 1
        return processed

    def verify_rebuild(self) -> bool:
        """Verifies projection state is consistent.

        Returns True if no duplicate proposal_ids exist.
        """
        all_projections = self.projection_repo.list_all(limit=10000)
        seen = set()
        for proj in all_projections:
            if proj.proposal_id in seen:
                return False
            seen.add(proj.proposal_id)
        return True

    def get_status_distribution(self) -> Dict[str, int]:
        """Returns count of proposals by status."""
        all_projections = self.projection_repo.list_all(limit=10000)
        distribution = {}
        for proj in all_projections:
            distribution[proj.status] = distribution.get(proj.status, 0) + 1
        return distribution
