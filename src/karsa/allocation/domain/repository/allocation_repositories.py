from abc import ABC, abstractmethod
from typing import Optional, List
from karsa.allocation.domain.models import AllocationSession, AllocationDecisionRecord

class AllocationSessionRepository(ABC):
    @abstractmethod
    def save(self, session: AllocationSession) -> None:
        """Saves or updates an AllocationSession aggregate, checking OCC version."""
        ...

    @abstractmethod
    def find_by_urn(self, session_urn: str) -> Optional[AllocationSession]:
        """Finds an AllocationSession aggregate by its URN."""
        ...


class AllocationDecisionRecordRepository(ABC):
    @abstractmethod
    def save(self, record: AllocationDecisionRecord) -> None:
        """Saves or updates an AllocationDecisionRecord, checking OCC version and enforcing trigger-like immutability."""
        ...

    @abstractmethod
    def find_by_urn(self, record_urn: str) -> Optional[AllocationDecisionRecord]:
        """Finds an AllocationDecisionRecord by its URN."""
        ...

    @abstractmethod
    def find_active_by_worker(self, worker_urn: str, limit: int, cursor: Optional[str] = None) -> List[AllocationDecisionRecord]:
        """Finds active AllocationDecisionRecords for a worker with keyset pagination (record_urn cursor)."""
        ...

    @abstractmethod
    def find_by_session_paginated(self, session_urn: str, limit: int, cursor: Optional[str] = None) -> List[AllocationDecisionRecord]:
        """Finds AllocationDecisionRecords for a session with keyset pagination (record_urn cursor)."""
        ...

    @abstractmethod
    def find_lineage(self, start_record_urn: str) -> List[AllocationDecisionRecord]:
        """Retrieves the full lineage chain for a record, traversing predecessors in a cycle-safe manner."""
        ...

    @abstractmethod
    def find_allocation_lineage(self, start_record_urn: str) -> List[AllocationDecisionRecord]:
        """Alias for find_lineage to support different callers."""
        ...
