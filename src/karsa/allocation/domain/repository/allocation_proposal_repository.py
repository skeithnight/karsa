from abc import ABC, abstractmethod
from typing import Optional, List
from karsa.allocation.domain.model.allocation_proposal import AllocationProposal


class AllocationProposalRepository(ABC):
    @abstractmethod
    def save_proposal(self, proposal: AllocationProposal) -> None:
        """Saves an allocation proposal to the write-once ledger."""
        pass

    @abstractmethod
    def get_proposal_by_id(self, proposal_id: str) -> Optional[AllocationProposal]:
        """Retrieves an allocation proposal by its ID."""
        pass

    @abstractmethod
    def list_proposals(self, limit: int = 50, offset: int = 0) -> List[AllocationProposal]:
        """Retrieves a paginated list of allocation proposals."""
        pass

    @abstractmethod
    def list_proposals_by_policy(self, policy_id: str, limit: int = 50, offset: int = 0) -> List[AllocationProposal]:
        """Retrieves proposals filtered by policy_id."""
        pass

    @abstractmethod
    def exists(self, proposal_id: str) -> bool:
        """Checks whether a proposal exists."""
        pass
