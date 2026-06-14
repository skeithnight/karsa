from abc import ABC, abstractmethod
from typing import Optional, List
from karsa.review.domain.model.review import ReviewSession, LearningFeedback
from karsa.review.domain.model.value_objects import ReviewTarget

class ReviewSessionRepository(ABC):
    @abstractmethod
    def save(self, session: ReviewSession) -> None:
        pass

    @abstractmethod
    def find_by_id(self, session_id: str) -> Optional[ReviewSession]:
        pass

    @abstractmethod
    def list_all(self) -> List[ReviewSession]:
        pass


class LearningFeedbackRepository(ABC):
    @abstractmethod
    def save(self, feedback: LearningFeedback) -> None:
        pass

    @abstractmethod
    def find_by_id(self, feedback_id: str) -> Optional[LearningFeedback]:
        pass

    @abstractmethod
    def list_all(self) -> List[LearningFeedback]:
        pass
