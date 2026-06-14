from abc import ABC, abstractmethod
from typing import Any, Dict

class EventPublisherPort(ABC):
    @abstractmethod
    def publish(self, event: Any) -> None:
        """Publishes domain events to the shared event bus."""
        pass

class SignatureValidationPort(ABC):
    @abstractmethod
    def validate_signature(self, target_context: str, signature: str, payload: Dict[str, Any]) -> bool:
        """Validates that the provided signature authorizes the action from the target context."""
        pass
