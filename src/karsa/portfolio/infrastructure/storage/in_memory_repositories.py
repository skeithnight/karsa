from typing import Optional, Dict
from karsa.portfolio.domain.repository.portfolio_repository import PortfolioRepository, PortfolioTargetSnapshotRepository, PortfolioDecisionRepository
from karsa.portfolio.domain.model.portfolio import Portfolio, PortfolioTargetSnapshot, PortfolioDecision

class InMemoryPortfolioRepository(PortfolioRepository):
    def __init__(self):
        self.storage: Dict[str, Portfolio] = {}

    def save(self, portfolio: Portfolio) -> None:
        import copy
        self.storage[portfolio.portfolio_id] = copy.deepcopy(portfolio)

    def get_by_id(self, portfolio_id: str) -> Optional[Portfolio]:
        import copy
        p = self.storage.get(portfolio_id)
        if p:
            return copy.deepcopy(p)
        return None

    def exists(self, portfolio_id: str) -> bool:
        return portfolio_id in self.storage

    def delete(self, portfolio_id: str) -> None:
        self.storage.pop(portfolio_id, None)

class InMemoryTargetSnapshotRepository(PortfolioTargetSnapshotRepository):
    def __init__(self):
        self.storage: Dict[str, PortfolioTargetSnapshot] = {}

    def save(self, snapshot: PortfolioTargetSnapshot) -> None:
        import copy
        self.storage[snapshot.snapshot_id] = copy.deepcopy(snapshot)

    def get_by_id(self, snapshot_id: str) -> Optional[PortfolioTargetSnapshot]:
        import copy
        s = self.storage.get(snapshot_id)
        if s:
            return copy.deepcopy(s)
        return None

    def exists(self, snapshot_id: str) -> bool:
        return snapshot_id in self.storage

    def delete(self, snapshot_id: str) -> None:
        self.storage.pop(snapshot_id, None)

class InMemoryDecisionRepository(PortfolioDecisionRepository):
    def __init__(self):
        self.storage: Dict[str, PortfolioDecision] = {}

    def save(self, decision: PortfolioDecision) -> None:
        import copy
        self.storage[decision.decision_id] = copy.deepcopy(decision)

    def get_by_id(self, decision_id: str) -> Optional[PortfolioDecision]:
        import copy
        d = self.storage.get(decision_id)
        if d:
            return copy.deepcopy(d)
        return None
