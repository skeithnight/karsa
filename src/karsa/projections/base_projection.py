from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseProjection(ABC):
    """Base class for all read model projections."""
    
    @abstractmethod
    def handle_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Process an event to update the read model."""
        pass

    @property
    @abstractmethod
    def projection_name(self) -> str:
        """Unique identifier for this projection."""
        pass
