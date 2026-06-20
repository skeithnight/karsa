from typing import TypeVar, Generic
from abc import ABC, abstractmethod

Q = TypeVar('Q')
R = TypeVar('R')

class QueryHandler(Generic[Q, R], ABC):
    """Base class for query handlers."""
    
    @abstractmethod
    def handle(self, query: Q) -> R:
        pass
