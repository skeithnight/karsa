"""InvestmentMemoRepository ABC -- Sprint-15."""

from abc import ABC, abstractmethod
from typing import List, Optional


class InvestmentMemoRepository(ABC):
    """Write-once repository for investment memos."""

    @abstractmethod
    def save(self, record) -> bool:
        """Persist a memo. Returns False on duplicate."""

    @abstractmethod
    def get_by_id(self, memo_id: str):
        """Lookup by memo_id URN."""

    @abstractmethod
    def get_by_decision_id(self, decision_id: str):
        """Lookup by decision_id."""

    @abstractmethod
    def get_by_ticker(self, ticker: str) -> List:
        """All memos for a ticker."""

    @abstractmethod
    def list_memos(self, page: int = 1, size: int = 50) -> List:
        """Paginated listing of all memos."""
