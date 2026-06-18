from typing import List
from abc import ABC, abstractmethod
from ..domain.event import DomainEvent

class EventOutbox(ABC):
    """Interface for an event outbox to guarantee delivery."""
    
    @abstractmethod
    def save_events(self, events: List[DomainEvent]) -> None:
        """Save events to the outbox transactionally."""
        pass
        
    @abstractmethod
    def get_unpublished_events(self, limit: int = 100) -> List[DomainEvent]:
        """Retrieve unpublished events for CDC/publishing."""
        pass
        
    @abstractmethod
    def mark_as_published(self, event_ids: List[str]) -> None:
        """Mark events as published to prevent replay."""
        pass
