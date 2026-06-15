from abc import ABC, abstractmethod
from typing import Optional, List
from karsa.performance.domain.model.models import PerformanceSession, WorkerEvaluationRecord

class PerformanceSessionRepository(ABC):
    @abstractmethod
    def save(self, session: PerformanceSession) -> None:
        pass

    @abstractmethod
    def get_by_id(self, session_id: str) -> Optional[PerformanceSession]:
        pass

    @abstractmethod
    def list_all(self) -> List[PerformanceSession]:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass


class WorkerEvaluationRepository(ABC):
    @abstractmethod
    def save(self, record: WorkerEvaluationRecord) -> None:
        pass

    @abstractmethod
    def find_by_id(self, record_id: str, version: int) -> Optional[WorkerEvaluationRecord]:
        pass

    @abstractmethod
    def find_active_by_worker(self, worker_urn: str) -> List[WorkerEvaluationRecord]:
        pass

    @abstractmethod
    def find_by_session(self, session_id: str) -> List[WorkerEvaluationRecord]:
        pass

    @abstractmethod
    def list_all(self) -> List[WorkerEvaluationRecord]:
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
