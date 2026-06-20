from typing import List
from abc import ABC, abstractmethod
from ..domain.event import DomainEvent

class EventPublisher(ABC):
    """Base interface for publishing domain events."""
    
    @abstractmethod
    def publish(self, events: List[DomainEvent]) -> None:
        """Publish a list of domain events."""
        pass
