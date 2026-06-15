import os
import json
import tempfile
from typing import Optional, List
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
from karsa.allocation.infrastructure.storage.in_memory_repositories import ConcurrencyConflictError

def _urn_to_id(urn: str) -> str:
    return urn.split(":")[-1]

class FileAllocationSessionRepository(AllocationSessionRepository):
    def __init__(self, storage_dir: str = ".karsa/allocation/sessions/"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._cleanup_orphaned_tmp_files()

    def _cleanup_orphaned_tmp_files(self) -> None:
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.endswith(".tmp"):
                    file_path = os.path.join(self.storage_dir, filename)
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
        except Exception:
            pass

    def _get_path(self, session_id: str) -> str:
        return os.path.join(self.storage_dir, f"{session_id}.json")

    def save(self, session: AllocationSession) -> None:
        path = self._get_path(session.session_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            existing_ver = data.get("aggregate_version", 1)
            if existing_ver != session.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"OCC Conflict: Expected version {existing_ver}, got {session.aggregate_version - 1}"
                )

        # Atomic Write
        temp_fd, temp_path = tempfile.mkstemp(dir=self.storage_dir, suffix=".tmp")
        try:
            with os.fdopen(temp_fd, "w") as f:
                # Deterministic serialization: sort_keys=True
                json.dump(session.to_dict(), f, indent=2, sort_keys=True)
            os.replace(temp_path, path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    def find_by_urn(self, session_urn: str) -> Optional[AllocationSession]:
        try:
            session_id = _urn_to_id(session_urn)
            path = self._get_path(session_id)
            if not os.path.exists(path):
                return None
            with open(path, "r") as f:
                data = json.load(f)
            return AllocationSession.from_dict(data)
        except Exception:
            return None


class FileAllocationDecisionRecordRepository(AllocationDecisionRecordRepository):
    def __init__(self, storage_dir: str = ".karsa/allocation/records/"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._cleanup_orphaned_tmp_files()

    def _cleanup_orphaned_tmp_files(self) -> None:
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.endswith(".tmp"):
                    file_path = os.path.join(self.storage_dir, filename)
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
        except Exception:
            pass

    def _get_path(self, record_id: str) -> str:
        return os.path.join(self.storage_dir, f"{record_id}.json")

    def save(self, record: AllocationDecisionRecord) -> None:
        path = self._get_path(record.record_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            existing_ver = data.get("aggregate_version", 1)
            # 1. OCC check
            if existing_ver != record.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"OCC Conflict: Expected version {existing_ver}, got {record.aggregate_version - 1}"
                )
            # 2. Immutability validation
            mutable_fields = {"is_active", "superseded_by_version", "invalidated_by_version", "aggregate_version"}
            new_dict = record.to_dict()
            for key, val in data.items():
                if key not in mutable_fields and new_dict.get(key) != val:
                    raise ImmutabilityViolationError(
                        f"Cannot modify immutable field '{key}' on AllocationDecisionRecord"
                    )

        # Atomic Write
        temp_fd, temp_path = tempfile.mkstemp(dir=self.storage_dir, suffix=".tmp")
        try:
            with os.fdopen(temp_fd, "w") as f:
                # Deterministic serialization: sort_keys=True
                json.dump(record.to_dict(), f, indent=2, sort_keys=True)
            os.replace(temp_path, path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    def find_by_urn(self, record_urn: str) -> Optional[AllocationDecisionRecord]:
        try:
            record_id = _urn_to_id(record_urn)
            path = self._get_path(record_id)
            if not os.path.exists(path):
                return None
            with open(path, "r") as f:
                data = json.load(f)
            return AllocationDecisionRecord.from_dict(data)
        except Exception:
            return None

    def _load_all_records(self) -> List[AllocationDecisionRecord]:
        records = []
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.endswith(".json") and not filename.endswith(".tmp"):
                    path = os.path.join(self.storage_dir, filename)
                    try:
                        with open(path, "r") as f:
                            data = json.load(f)
                        records.append(AllocationDecisionRecord.from_dict(data))
                    except Exception:
                        pass
        except Exception:
            pass
        return records

    def find_active_by_worker(self, worker_urn: str, limit: int, cursor: Optional[str] = None) -> List[AllocationDecisionRecord]:
        all_rec = self._load_all_records()
        matched = [r for r in all_rec if r.worker_urn == worker_urn and r.is_active]
        matched.sort(key=lambda x: x.record_urn)

        result = []
        for r in matched:
            if cursor and r.record_urn <= cursor:
                continue
            result.append(r)
            if len(result) == limit:
                break
        return result

    def find_by_session_paginated(self, session_urn: str, limit: int, cursor: Optional[str] = None) -> List[AllocationDecisionRecord]:
        all_rec = self._load_all_records()
        matched = [r for r in all_rec if r.session_urn == session_urn]
        matched.sort(key=lambda x: x.record_urn)

        result = []
        for r in matched:
            if cursor and r.record_urn <= cursor:
                continue
            result.append(r)
            if len(result) == limit:
                break
        return result

    def find_lineage(self, start_record_urn: str) -> List[AllocationDecisionRecord]:
        all_rec = self._load_all_records()
        return reconstruct_allocation_lineage(all_rec, start_record_urn)

    def find_allocation_lineage(self, start_record_urn: str) -> List[AllocationDecisionRecord]:
        return self.find_lineage(start_record_urn)
