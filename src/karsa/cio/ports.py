from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class DecisionJournalPort(ABC):
    @abstractmethod
    def verify_journal_exists(self, journal_ref: str) -> bool:
        """Verifies if the specified Decision Journal URN exists and is sealed."""
        pass

    @abstractmethod
    def get_journal_expectations(self, journal_ref: str) -> Dict[str, Any]:
        """Retrieves ex-ante expectations (expected_return, confidence) from the Decision Journal."""
        pass

class GovernanceExceptionPort(ABC):
    @abstractmethod
    def verify_exception_token(self, exception_id: str, signature: str, payload: Dict[str, Any]) -> bool:
        """Verifies if a Governance exception token is valid and signed by Governance authority."""
        pass

class AllocationPort(ABC):
    @abstractmethod
    def request_recalculation(self, calculation_id: str, constraints: Dict[str, Any]) -> None:
        """Dispatches a recalculation request to the Capital Allocation Engine with updated constraints."""
        pass

class EventPublisherPort(ABC):
    @abstractmethod
    def publish(self, event: Any) -> None:
        """Publishes domain events to the shared event bus."""
        pass
