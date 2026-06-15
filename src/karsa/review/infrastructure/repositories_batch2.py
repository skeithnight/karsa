import os
import json
import tempfile
import threading
from typing import Optional, List, Dict
from karsa.review.domain.models import ReviewSession, ReviewRecord, PostMortemRecord
from karsa.review.domain.repositories import ReviewSessionRepository, ReviewRecordRepository, PostMortemRecordRepository
from karsa.review.domain.lineage import reconstruct_review_lineage, reconstruct_postmortem_lineage

class ConcurrencyConflictError(Exception):
    pass


def _urn_to_id(urn: str) -> str:
    return urn.split(":")[-1]


class InMemoryReviewSessionRepository(ReviewSessionRepository):
    def __init__(self):
        self._sessions: Dict[str, ReviewSession] = {}
        self._lock = threading.Lock()

    def save(self, session: ReviewSession) -> None:
        with self._lock:
            existing = self._sessions.get(session.session_id)
            if existing:
                if existing.aggregate_version != session.aggregate_version - 1:
                    raise ConcurrencyConflictError(
                        f"OCC Conflict: Expected version {existing.aggregate_version}, got {session.aggregate_version - 1}"
                    )
            # Deepcopy protection via serialization round-trip
            self._sessions[session.session_id] = ReviewSession.from_dict(session.to_dict())

    def find_by_id(self, session_id: str) -> Optional[ReviewSession]:
        with self._lock:
            sess = self._sessions.get(session_id)
            if not sess:
                return None
            return ReviewSession.from_dict(sess.to_dict())

    def find_by_urn(self, session_urn: str) -> Optional[ReviewSession]:
        with self._lock:
            for sess in self._sessions.values():
                if sess.session_urn == session_urn:
                    return ReviewSession.from_dict(sess.to_dict())
            return None


class InMemoryReviewRecordRepository(ReviewRecordRepository):
    def __init__(self):
        self._records: Dict[str, ReviewRecord] = {}
        self._lock = threading.Lock()

    def save(self, record: ReviewRecord) -> None:
        with self._lock:
            existing = self._records.get(record.record_id)
            if existing:
                if existing.aggregate_version != record.aggregate_version - 1:
                    raise ConcurrencyConflictError(
                        f"OCC Conflict: Expected version {existing.aggregate_version}, got {record.aggregate_version - 1}"
                    )
            self._records[record.record_id] = ReviewRecord.from_dict(record.to_dict())

    def find_by_id(self, record_id: str) -> Optional[ReviewRecord]:
        with self._lock:
            rec = self._records.get(record_id)
            if not rec:
                return None
            return ReviewRecord.from_dict(rec.to_dict())

    def find_by_urn(self, record_urn: str) -> Optional[ReviewRecord]:
        with self._lock:
            for rec in self._records.values():
                if rec.record_urn == record_urn:
                    return ReviewRecord.from_dict(rec.to_dict())
            return None

    def find_active_by_worker(self, worker_urn: str, limit: int, cursor: Optional[str] = None) -> List[ReviewRecord]:
        with self._lock:
            matched = []
            for rec in self._records.values():
                if rec.worker_urn == worker_urn and rec.is_active:
                    matched.append(rec)
            
            # Keyset pagination: sort alphabetically by record_urn
            matched.sort(key=lambda x: x.record_urn)
            
            result = []
            for r in matched:
                if cursor and r.record_urn <= cursor:
                    continue
                result.append(ReviewRecord.from_dict(r.to_dict()))
                if len(result) == limit:
                    break
            return result

    def find_by_session_paginated(self, session_urn: str, limit: int, cursor: Optional[str] = None) -> List[ReviewRecord]:
        with self._lock:
            matched = []
            for rec in self._records.values():
                if rec.session_urn == session_urn:
                    matched.append(rec)
            
            matched.sort(key=lambda x: x.record_urn)
            
            result = []
            for r in matched:
                if cursor and r.record_urn <= cursor:
                    continue
                result.append(ReviewRecord.from_dict(r.to_dict()))
                if len(result) == limit:
                    break
            return result

    def find_review_lineage(self, start_record_urn: str) -> List[ReviewRecord]:
        with self._lock:
            all_records = [ReviewRecord.from_dict(r.to_dict()) for r in self._records.values()]
            return reconstruct_review_lineage(all_records, start_record_urn)


class InMemoryPostMortemRecordRepository(PostMortemRecordRepository):
    def __init__(self):
        self._postmortems: Dict[str, PostMortemRecord] = {}
        self._lock = threading.Lock()

    def save(self, postmortem: PostMortemRecord) -> None:
        with self._lock:
            existing = self._postmortems.get(postmortem.postmortem_id)
            if existing:
                if existing.aggregate_version != postmortem.aggregate_version - 1:
                    raise ConcurrencyConflictError(
                        f"OCC Conflict: Expected version {existing.aggregate_version}, got {postmortem.aggregate_version - 1}"
                    )
            self._postmortems[postmortem.postmortem_id] = PostMortemRecord.from_dict(postmortem.to_dict())

    def find_by_id(self, postmortem_id: str) -> Optional[PostMortemRecord]:
        with self._lock:
            pm = self._postmortems.get(postmortem_id)
            if not pm:
                return None
            return PostMortemRecord.from_dict(pm.to_dict())

    def find_by_urn(self, postmortem_urn: str) -> Optional[PostMortemRecord]:
        with self._lock:
            for pm in self._postmortems.values():
                if pm.postmortem_urn == postmortem_urn:
                    return PostMortemRecord.from_dict(pm.to_dict())
            return None

    def find_by_session_paginated(self, session_urn: str, limit: int, cursor: Optional[str] = None) -> List[PostMortemRecord]:
        with self._lock:
            matched = []
            for pm in self._postmortems.values():
                if pm.session_urn == session_urn:
                    matched.append(pm)
            
            matched.sort(key=lambda x: x.postmortem_urn)
            
            result = []
            for pm in matched:
                if cursor and pm.postmortem_urn <= cursor:
                    continue
                result.append(PostMortemRecord.from_dict(pm.to_dict()))
                if len(result) == limit:
                    break
            return result

    def find_postmortem_lineage(self, start_postmortem_urn: str) -> List[PostMortemRecord]:
        with self._lock:
            all_pm = [PostMortemRecord.from_dict(pm.to_dict()) for pm in self._postmortems.values()]
            return reconstruct_postmortem_lineage(all_pm, start_postmortem_urn)


# FILE REPOSITORIES WITH ATOMIC WRITES AND CURSOR PAGINATION

class FileReviewSessionRepository(ReviewSessionRepository):
    def __init__(self, storage_dir: str = ".karsa/review_postmortem/sessions/"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, session_id: str) -> str:
        return os.path.join(self.storage_dir, f"{session_id}.json")

    def save(self, session: ReviewSession) -> None:
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
                json.dump(session.to_dict(), f, indent=2)
            os.replace(temp_path, path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    def find_by_id(self, session_id: str) -> Optional[ReviewSession]:
        path = self._get_path(session_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return ReviewSession.from_dict(data)

    def find_by_urn(self, session_urn: str) -> Optional[ReviewSession]:
        # O(1) retrieval using URN to ID mapping
        try:
            session_id = _urn_to_id(session_urn)
            return self.find_by_id(session_id)
        except Exception:
            return None


class FileReviewRecordRepository(ReviewRecordRepository):
    def __init__(self, storage_dir: str = ".karsa/review_postmortem/records/"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, record_id: str) -> str:
        return os.path.join(self.storage_dir, f"{record_id}.json")

    def save(self, record: ReviewRecord) -> None:
        path = self._get_path(record.record_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            existing_ver = data.get("aggregate_version", 1)
            if existing_ver != record.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"OCC Conflict: Expected version {existing_ver}, got {record.aggregate_version - 1}"
                )
        
        temp_fd, temp_path = tempfile.mkstemp(dir=self.storage_dir, suffix=".tmp")
        try:
            with os.fdopen(temp_fd, "w") as f:
                json.dump(record.to_dict(), f, indent=2)
            os.replace(temp_path, path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    def find_by_id(self, record_id: str) -> Optional[ReviewRecord]:
        path = self._get_path(record_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return ReviewRecord.from_dict(data)

    def find_by_urn(self, record_urn: str) -> Optional[ReviewRecord]:
        try:
            record_id = _urn_to_id(record_urn)
            return self.find_by_id(record_id)
        except Exception:
            return None

    def _load_all_records(self) -> List[ReviewRecord]:
        records = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json") and not filename.endswith(".tmp"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    records.append(ReviewRecord.from_dict(data))
                except Exception:
                    pass
        return records

    def find_active_by_worker(self, worker_urn: str, limit: int, cursor: Optional[str] = None) -> List[ReviewRecord]:
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

    def find_by_session_paginated(self, session_urn: str, limit: int, cursor: Optional[str] = None) -> List[ReviewRecord]:
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

    def find_review_lineage(self, start_record_urn: str) -> List[ReviewRecord]:
        all_rec = self._load_all_records()
        return reconstruct_review_lineage(all_rec, start_record_urn)


class FilePostMortemRecordRepository(PostMortemRecordRepository):
    def __init__(self, storage_dir: str = ".karsa/review_postmortem/postmortems/"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, postmortem_id: str) -> str:
        return os.path.join(self.storage_dir, f"{postmortem_id}.json")

    def save(self, postmortem: PostMortemRecord) -> None:
        path = self._get_path(postmortem.postmortem_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            existing_ver = data.get("aggregate_version", 1)
            if existing_ver != postmortem.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"OCC Conflict: Expected version {existing_ver}, got {postmortem.aggregate_version - 1}"
                )
        
        temp_fd, temp_path = tempfile.mkstemp(dir=self.storage_dir, suffix=".tmp")
        try:
            with os.fdopen(temp_fd, "w") as f:
                json.dump(postmortem.to_dict(), f, indent=2)
            os.replace(temp_path, path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    def find_by_id(self, postmortem_id: str) -> Optional[PostMortemRecord]:
        path = self._get_path(postmortem_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return PostMortemRecord.from_dict(data)

    def find_by_urn(self, postmortem_urn: str) -> Optional[PostMortemRecord]:
        try:
            postmortem_id = _urn_to_id(postmortem_urn)
            return self.find_by_id(postmortem_id)
        except Exception:
            return None

    def _load_all_pms(self) -> List[PostMortemRecord]:
        pms = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json") and not filename.endswith(".tmp"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    pms.append(PostMortemRecord.from_dict(data))
                except Exception:
                    pass
        return pms

    def find_by_session_paginated(self, session_urn: str, limit: int, cursor: Optional[str] = None) -> List[PostMortemRecord]:
        all_pm = self._load_all_pms()
        matched = [pm for pm in all_pm if pm.session_urn == session_urn]
        matched.sort(key=lambda x: x.postmortem_urn)
        
        result = []
        for pm in matched:
            if cursor and pm.postmortem_urn <= cursor:
                continue
            result.append(pm)
            if len(result) == limit:
                break
        return result

    def find_postmortem_lineage(self, start_postmortem_urn: str) -> List[PostMortemRecord]:
        all_pm = self._load_all_pms()
        return reconstruct_postmortem_lineage(all_pm, start_postmortem_urn)
