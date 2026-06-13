import abc
from typing import Optional
from karsa.portfolio.domain.model.portfolio import Portfolio, PortfolioTargetSnapshot, PortfolioDecision

class PortfolioRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, portfolio: Portfolio) -> None:
        pass
        
    @abc.abstractmethod
    def get_by_id(self, portfolio_id: str) -> Optional[Portfolio]:
        pass
        
    @abc.abstractmethod
    def exists(self, portfolio_id: str) -> bool:
        pass
        
    @abc.abstractmethod
    def delete(self, portfolio_id: str) -> None:
        pass

class PortfolioTargetSnapshotRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, snapshot: PortfolioTargetSnapshot) -> None:
        pass
        
    @abc.abstractmethod
    def get_by_id(self, snapshot_id: str) -> Optional[PortfolioTargetSnapshot]:
        pass
        
    @abc.abstractmethod
    def exists(self, snapshot_id: str) -> bool:
        pass
        
    @abc.abstractmethod
    def delete(self, snapshot_id: str) -> None:
        pass

class PortfolioDecisionRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, decision: PortfolioDecision) -> None:
        pass
        
    @abc.abstractmethod
    def get_by_id(self, decision_id: str) -> Optional[PortfolioDecision]:
        pass
