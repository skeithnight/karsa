"""InvestmentDecisionPort -- Sprint-13. ADR-140.

Port interface for investment decision persistence.
Application layer owns this interface; infrastructure implements it.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional


class InvestmentDecisionPort(ABC):
    """Write-once port for investment decisions."""

    @abstractmethod
    def save(self, record: Any) -> bool:
        """Persist a decision. Returns False on duplicate."""

    @abstractmethod
    def get_by_id(self, decision_id: str) -> Optional[Any]:
        """Technical lookup by decision_id URN."""

    @abstractmethod
    def get_by_family_and_ticker(
        self, capability_family_id: str, ticker: str
    ) -> List[Any]:
        """All decisions for a family+ticker pair."""

    @abstractmethod
    def list_decisions(self, page: int = 1, size: int = 50) -> List[Any]:
        """Paginated listing of all decisions."""
