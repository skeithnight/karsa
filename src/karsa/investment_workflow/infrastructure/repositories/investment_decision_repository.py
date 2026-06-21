"""InvestmentDecisionRepository ABC -- Sprint-13. ADR-140."""

from abc import ABC, abstractmethod
from typing import List, Optional


class InvestmentDecisionRepository(ABC):
    """Write-once repository for investment decisions.

    Same pattern as CapabilityEvolutionRepository.
    """

    @abstractmethod
    def save(self, record) -> bool:
        """Persist a decision. Returns False on duplicate."""

    @abstractmethod
    def get_by_id(self, decision_id: str):
        """Technical lookup by decision_id URN."""

    @abstractmethod
    def get_by_family_and_ticker(
        self, capability_family_id: str, ticker: str
    ) -> List:
        """All decisions for a family+ticker pair."""

    @abstractmethod
    def list_decisions(self, page: int = 1, size: int = 50) -> List:
        """Paginated listing of all decisions."""
