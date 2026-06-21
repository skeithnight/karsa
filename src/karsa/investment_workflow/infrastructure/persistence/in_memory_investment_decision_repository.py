"""In-memory InvestmentDecisionRepository -- Sprint-13."""

from typing import Dict, List, Optional

from karsa.investment_workflow.domain.aggregates.investment_decision import (
    InvestmentDecision,
)
from karsa.investment_workflow.infrastructure.repositories.investment_decision_repository import (
    InvestmentDecisionRepository,
)


class InMemoryInvestmentDecisionRepository(InvestmentDecisionRepository):
    """In-memory write-once repository for testing."""

    def __init__(self) -> None:
        self._store: Dict[str, InvestmentDecision] = {}
        self._business_key: Dict[tuple, str] = {}

    def save(self, record: InvestmentDecision) -> bool:
        key = (record.capability_family_id, record.ticker, record.decision_date)
        if key in self._business_key:
            return False
        self._store[record.decision_id] = record
        self._business_key[key] = record.decision_id
        return True

    def get_by_id(self, decision_id: str) -> Optional[InvestmentDecision]:
        return self._store.get(decision_id)

    def get_by_family_and_ticker(
        self, capability_family_id: str, ticker: str
    ) -> List[InvestmentDecision]:
        return [
            d
            for d in self._store.values()
            if d.capability_family_id == capability_family_id
            and d.ticker == ticker
        ]

    def list_decisions(
        self, page: int = 1, size: int = 50
    ) -> List[InvestmentDecision]:
        items = list(self._store.values())
        start = (page - 1) * size
        return items[start : start + size]
