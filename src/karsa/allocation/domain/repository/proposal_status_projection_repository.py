from abc import ABC, abstractmethod
from typing import Optional, List

from karsa.allocation.domain.model.proposal_status_projection import ProposalStatusProjection


class ProposalStatusProjectionRepository(ABC):
    @abstractmethod
    def get_status(self, proposal_id: str) -> Optional[ProposalStatusProjection]:
        """Returns the status projection for a proposal."""
        pass

    @abstractmethod
    def list_by_status(self, status: str, limit: int = 50, offset: int = 0) -> List[ProposalStatusProjection]:
        """Returns proposals filtered by status."""
        pass

    @abstractmethod
    def list_all(self, limit: int = 100, offset: int = 0) -> List[ProposalStatusProjection]:
        """Returns all proposal status projections (for replay verification)."""
        pass

    @abstractmethod
    def upsert_pending(self, proposal_id: str, event_sequence: int) -> None:
        """Inserts a PENDING status for a new proposal."""
        pass

    @abstractmethod
    def mark_approved(self, proposal_id: str, decision_id: str, decided_by: str, decided_at: str, event_sequence: int) -> None:
        """Updates status to APPROVED."""
        pass

    @abstractmethod
    def mark_rejected(self, proposal_id: str, decision_id: str, decided_by: str, decided_at: str, event_sequence: int) -> None:
        """Updates status to REJECTED."""
        pass

    @abstractmethod
    def mark_modified(self, proposal_id: str, decision_id: str, decided_by: str, decided_at: str, event_sequence: int) -> None:
        """Updates status to MODIFIED."""
        pass

    @abstractmethod
    def mark_expired(self, proposal_id: str, decided_at: str, event_sequence: int) -> None:
        """Updates status to EXPIRED."""
        pass
