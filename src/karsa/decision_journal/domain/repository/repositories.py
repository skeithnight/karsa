from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime
from karsa.decision_journal.domain.models import DecisionJournalEntry

class DecisionJournalRepository(ABC):
    @abstractmethod
    def append(self, entry: DecisionJournalEntry) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def get_by_urn(self, journal_urn: str) -> Optional[DecisionJournalEntry]:
        pass  # pragma: no cover

    @abstractmethod
    def fetch_latest_by_thesis(self, thesis_urn: str) -> Optional[DecisionJournalEntry]:
        pass  # pragma: no cover
        
    @abstractmethod
    def fetch_latest_by_worker(self, worker_urn: str) -> Optional[DecisionJournalEntry]:
        pass  # pragma: no cover
        
    @abstractmethod
    def fetch_lineage(self, journal_urn: str) -> List[DecisionJournalEntry]:
        pass  # pragma: no cover

    @abstractmethod
    def fetch_by_time_range(self, start_dt: datetime, end_dt: datetime) -> List[DecisionJournalEntry]:
        pass  # pragma: no cover
