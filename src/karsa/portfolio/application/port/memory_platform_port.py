import abc
from karsa.portfolio.domain.model.portfolio import PortfolioTargetSnapshot, PortfolioDecision

class MemoryPlatformPort(abc.ABC):
    @abc.abstractmethod
    def publish_target_snapshot(self, snapshot: PortfolioTargetSnapshot) -> None:
        pass
        
    @abc.abstractmethod
    def publish_portfolio_decision(self, decision: PortfolioDecision) -> None:
        pass
