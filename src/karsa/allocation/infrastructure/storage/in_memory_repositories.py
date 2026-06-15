import threading
from typing import Optional, List, Dict
from karsa.allocation.domain.models import (
    AllocationSession,
    AllocationDecisionRecord,
    ImmutabilityViolationError
)
from karsa.allocation.domain.repository.allocation_repositories import (
    AllocationSessionRepository,
    AllocationDecisionRecordRepository
)
from karsa.allocation.domain.lineage import reconstruct_allocation_lineage

class ConcurrencyConflictError(Exception):
    pass

class InMemoryAllocationSessionRepository(AllocationSessionRepository):
    def __init__(self):
        self._sessions: Dict[str, AllocationSession] = {}
        self._lock = threading.Lock()

    def save(self, session: AllocationSession) -> None:
        with self._lock:
            existing = self._sessions.get(session.session_id)
            if existing:
                if existing.aggregate_version != session.aggregate_version - 1:
                    raise ConcurrencyConflictError(
                        f"OCC Conflict: Expected version {existing.aggregate_version}, got {session.aggregate_version - 1}"
                    )
            # Deepcopy isolation via to_dict/from_dict
            self._sessions[session.session_id] = AllocationSession.from_dict(session.to_dict())

    def find_by_urn(self, session_urn: str) -> Optional[AllocationSession]:
        with self._lock:
            for session in self._sessions.values():
                if session.session_urn == session_urn:
                    return AllocationSession.from_dict(session.to_dict())
            return None


class InMemoryAllocationDecisionRecordRepository(AllocationDecisionRecordRepository):
    def __init__(self):
        self._records: Dict[str, AllocationDecisionRecord] = {}
        self._lock = threading.Lock()

    def save(self, record: AllocationDecisionRecord) -> None:
        with self._lock:
            existing = self._records.get(record.record_id)
            if existing:
                # 1. OCC check
                if existing.aggregate_version != record.aggregate_version - 1:
                    raise ConcurrencyConflictError(
                        f"OCC Conflict: Expected version {existing.aggregate_version}, got {record.aggregate_version - 1}"
                    )
                # 2. Immutability validation (simulate DB trigger)
                existing_dict = existing.to_dict()
                new_dict = record.to_dict()
                mutable_fields = {"is_active", "superseded_by_version", "invalidated_by_version", "aggregate_version"}
                for key, val in existing_dict.items():
                    if key not in mutable_fields and new_dict.get(key) != val:
                        raise ImmutabilityViolationError(
                            f"Cannot modify immutable field '{key}' on AllocationDecisionRecord"
                        )

            # Deepcopy isolation via to_dict/from_dict
            self._records[record.record_id] = AllocationDecisionRecord.from_dict(record.to_dict())

    def find_by_urn(self, record_urn: str) -> Optional[AllocationDecisionRecord]:
        with self._lock:
            for record in self._records.values():
                if record.record_urn == record_urn:
                    return AllocationDecisionRecord.from_dict(record.to_dict())
            return None

    def find_active_by_worker(self, worker_urn: str, limit: int, cursor: Optional[str] = None) -> List[AllocationDecisionRecord]:
        with self._lock:
            matched = []
            for record in self._records.values():
                if record.worker_urn == worker_urn and record.is_active:
                    matched.append(record)

            # Keyset pagination: sort alphabetically by record_urn ascending
            matched.sort(key=lambda x: x.record_urn)

            result = []
            for r in matched:
                if cursor and r.record_urn <= cursor:
                    continue
                result.append(AllocationDecisionRecord.from_dict(r.to_dict()))
                if len(result) == limit:
                    break
            return result

    def find_by_session_paginated(self, session_urn: str, limit: int, cursor: Optional[str] = None) -> List[AllocationDecisionRecord]:
        with self._lock:
            matched = []
            for record in self._records.values():
                if record.session_urn == session_urn:
                    matched.append(record)

            # Keyset pagination: sort alphabetically by record_urn ascending
            matched.sort(key=lambda x: x.record_urn)

            result = []
            for r in matched:
                if cursor and r.record_urn <= cursor:
                    continue
                result.append(AllocationDecisionRecord.from_dict(r.to_dict()))
                if len(result) == limit:
                    break
            return result

    def find_lineage(self, start_record_urn: str) -> List[AllocationDecisionRecord]:
        with self._lock:
            records_list = [AllocationDecisionRecord.from_dict(r.to_dict()) for r in self._records.values()]
            return reconstruct_allocation_lineage(records_list, start_record_urn)

    def find_allocation_lineage(self, start_record_urn: str) -> List[AllocationDecisionRecord]:
        return self.find_lineage(start_record_urn)
