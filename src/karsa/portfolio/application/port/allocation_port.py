import abc
from typing import List
from karsa.allocation.domain.model.allocation import RiskAllocation
from karsa.portfolio.domain.model.portfolio import AllocationPortfolioMapping

class AllocationPort(abc.ABC):
    @abc.abstractmethod
    def get_allocations_for_portfolio(self, portfolio_id: str) -> List[RiskAllocation]:
        pass
        
    @abc.abstractmethod
    def get_mappings_for_portfolio(self, portfolio_id: str) -> List[AllocationPortfolioMapping]:
        pass
