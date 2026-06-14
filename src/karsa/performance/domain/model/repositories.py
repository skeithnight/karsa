from abc import ABC, abstractmethod
from typing import Optional, List
from karsa.performance.domain.model.evaluation import DecisionEvaluation, EvaluationSnapshot
from karsa.performance.domain.model.value_objects import EvaluationTarget

class DecisionEvaluationRepository(ABC):
    @abstractmethod
    def save(self, evaluation: DecisionEvaluation) -> None:
        pass

    @abstractmethod
    def find_by_decision(self, decision_id: str) -> Optional[DecisionEvaluation]:
        pass

    @abstractmethod
    def list_all(self) -> List[DecisionEvaluation]:
        pass


class EvaluationSnapshotRepository(ABC):
    @abstractmethod
    def save(self, snapshot: EvaluationSnapshot) -> None:
        pass

    @abstractmethod
    def find_by_id(self, snapshot_id: str) -> Optional[EvaluationSnapshot]:
        pass

    @abstractmethod
    def list_by_target(self, target: EvaluationTarget) -> List[EvaluationSnapshot]:
        pass

    @abstractmethod
    def list_all(self) -> List[EvaluationSnapshot]:
        pass
