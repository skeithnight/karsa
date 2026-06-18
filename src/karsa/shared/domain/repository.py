from typing import TypeVar, Generic, Optional
from abc import ABC, abstractmethod
from .aggregate import AggregateRoot

T = TypeVar('T', bound=AggregateRoot)

class Repository(Generic[T], ABC):
    """Base repository interface."""
    
    @abstractmethod
    def add(self, aggregate: T) -> None:
        pass
        
    @abstractmethod
    def get(self, id: str) -> Optional[T]:
        pass
