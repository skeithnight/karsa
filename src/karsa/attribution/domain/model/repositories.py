from abc import ABC, abstractmethod
from typing import Optional, List
from karsa.attribution.domain.model.models import AttributionSession, PerformanceAttributionRecord

class AttributionSessionRepository(ABC):
    @abstractmethod
    def save(self, session: AttributionSession) -> None:
        pass

    @abstractmethod
    def get_by_id(self, session_id: str) -> Optional[AttributionSession]:
        pass

    @abstractmethod
    def list_all(self) -> List[AttributionSession]:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass


class PerformanceAttributionRepository(ABC):
    @abstractmethod
    def save(self, record: PerformanceAttributionRecord) -> None:
        pass

    @abstractmethod
    def find_by_id(self, record_id: str, version: int) -> Optional[PerformanceAttributionRecord]:
        pass

    @abstractmethod
    def find_active_by_decision(self, decision_id: str) -> List[PerformanceAttributionRecord]:
        pass

    @abstractmethod
    def find_by_session(self, session_id: str) -> List[PerformanceAttributionRecord]:
        pass

    @abstractmethod
    def list_all(self) -> List[PerformanceAttributionRecord]:
        pass

    @abstractmethod
    def deactivate_old_versions(self, decision_id: str, exclude_version: int) -> None:
        pass

    @abstractmethod
    def deactivate_by_session(self, session_id: str) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass
