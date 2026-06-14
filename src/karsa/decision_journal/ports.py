from abc import ABC, abstractmethod
from typing import Any, Dict
from karsa.decision_journal.value_objects import DecisionContextSnapshot

class ObjectStorePort(ABC):
    @abstractmethod
    def save_context_snapshot(self, decision_id: str, snapshot: DecisionContextSnapshot) -> str:
        """Saves a context snapshot to the object store and returns the URI."""
        pass

    @abstractmethod
    def get_context_snapshot(self, uri: str) -> DecisionContextSnapshot:
        """Retrieves a context snapshot from the object store using the URI."""
        pass

    @abstractmethod
    def verify_hash(self, snapshot: DecisionContextSnapshot, expected_hash: str) -> bool:
        """Computes the checksum of the snapshot and verifies it matches the expected hash."""
        pass

class EventPublisherPort(ABC):
    @abstractmethod
    def publish(self, event: Any) -> None:
        """Publishes an event to the system event bus."""
        pass
