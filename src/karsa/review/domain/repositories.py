from abc import ABC, abstractmethod
from typing import Optional, List
from karsa.review.domain.models import ReviewSession, ReviewRecord, PostMortemRecord

class ReviewSessionRepository(ABC):
    @abstractmethod
    def save(self, session: ReviewSession) -> None:
        pass

    @abstractmethod
    def find_by_id(self, session_id: str) -> Optional[ReviewSession]:
        pass

    @abstractmethod
    def find_by_urn(self, session_urn: str) -> Optional[ReviewSession]:
        pass


class ReviewRecordRepository(ABC):
    @abstractmethod
    def save(self, record: ReviewRecord) -> None:
        pass

    @abstractmethod
    def find_by_id(self, record_id: str) -> Optional[ReviewRecord]:
        pass

    @abstractmethod
    def find_by_urn(self, record_urn: str) -> Optional[ReviewRecord]:
        pass

    @abstractmethod
    def find_active_by_worker(self, worker_urn: str, limit: int, cursor: Optional[str] = None) -> List[ReviewRecord]:
        pass

    @abstractmethod
    def find_by_session_paginated(self, session_urn: str, limit: int, cursor: Optional[str] = None) -> List[ReviewRecord]:
        pass

    @abstractmethod
    def find_review_lineage(self, start_record_urn: str) -> List[ReviewRecord]:
        pass


class PostMortemRecordRepository(ABC):
    @abstractmethod
    def save(self, postmortem: PostMortemRecord) -> None:
        pass

    @abstractmethod
    def find_by_id(self, postmortem_id: str) -> Optional[PostMortemRecord]:
        pass

    @abstractmethod
    def find_by_urn(self, postmortem_urn: str) -> Optional[PostMortemRecord]:
        pass

    @abstractmethod
    def find_by_session_paginated(self, session_urn: str, limit: int, cursor: Optional[str] = None) -> List[PostMortemRecord]:
        pass

    @abstractmethod
    def find_postmortem_lineage(self, start_postmortem_urn: str) -> List[PostMortemRecord]:
        pass
