import abc
from typing import Optional
from karsa.allocation.domain.model.allocation import RiskAllocation

class AllocationRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, allocation: RiskAllocation) -> None:
        pass
        
    @abc.abstractmethod
    def get_by_id(self, allocation_id: str) -> Optional[RiskAllocation]:
        pass
        
    @abc.abstractmethod
    def exists(self, allocation_id: str) -> bool:
        pass
        
    @abc.abstractmethod
    def delete(self, allocation_id: str) -> None:
        pass
