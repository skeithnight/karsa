"""In-memory InvestmentMemoRepository -- Sprint-15."""

from typing import Dict, List, Optional

from karsa.investment_memo.domain.aggregates.investment_memo import (
    InvestmentMemo,
)
from karsa.investment_memo.infrastructure.repositories.investment_memo_repository import (
    InvestmentMemoRepository,
)


class InMemoryInvestmentMemoRepository(InvestmentMemoRepository):
    """In-memory write-once repository for testing."""

    def __init__(self) -> None:
        self._store: Dict[str, InvestmentMemo] = {}
        self._decision_key: Dict[str, str] = {}

    def save(self, record: InvestmentMemo) -> bool:
        if record.decision_id in self._decision_key:
            return False
        self._store[record.memo_id] = record
        self._decision_key[record.decision_id] = record.memo_id
        return True

    def get_by_id(self, memo_id: str) -> Optional[InvestmentMemo]:
        return self._store.get(memo_id)

    def get_by_decision_id(self, decision_id: str) -> Optional[InvestmentMemo]:
        memo_id = self._decision_key.get(decision_id)
        return self._store.get(memo_id) if memo_id else None

    def get_by_ticker(self, ticker: str) -> List[InvestmentMemo]:
        return [m for m in self._store.values() if m.ticker == ticker]

    def list_memos(
        self, page: int = 1, size: int = 50
    ) -> List[InvestmentMemo]:
        items = list(self._store.values())
        start = (page - 1) * size
        return items[start : start + size]
