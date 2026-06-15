import os
import json
import copy
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict
from karsa.performance.domain.model.models import PerformanceSession, WorkerEvaluationRecord
from karsa.performance.domain.model.repositories import PerformanceSessionRepository, WorkerEvaluationRepository
from karsa.shared.infrastructure.uow import ConcurrencyConflictError

# ==========================================
# 1. InMemory Repositories
# ==========================================

class InMemoryPerformanceSessionRepository(PerformanceSessionRepository):
    def __init__(self):
        self._sessions: Dict[str, PerformanceSession] = {}

    def save(self, session: PerformanceSession) -> None:
        sid = session.session_id
        if sid in self._sessions:
            existing = self._sessions[sid]
            if existing.aggregate_version != session.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict on session {sid}: expected version {existing.aggregate_version}, got {session.aggregate_version}"
                )
        self._sessions[sid] = copy.deepcopy(session)

    def get_by_id(self, session_id: str) -> Optional[PerformanceSession]:
        session = self._sessions.get(session_id)
        if session:
            return copy.deepcopy(session)
        return None

    def list_all(self) -> List[PerformanceSession]:
        return [copy.deepcopy(s) for s in self._sessions.values()]

    def clear(self) -> None:
        self._sessions.clear()


class InMemoryWorkerEvaluationRepository(WorkerEvaluationRepository):
    def __init__(self):
        self._records: Dict[str, WorkerEvaluationRecord] = {}

    def save(self, record: WorkerEvaluationRecord) -> None:
        key = f"{record.record_id}:{record.evaluation_version}"
        if key in self._records:
            raise ValueError(f"Worker evaluation record already exists: {key}")
        self._records[key] = copy.deepcopy(record)

    def find_by_id(self, record_id: str, version: int) -> Optional[WorkerEvaluationRecord]:
        rec = self._records.get(f"{record_id}:{version}")
        if rec:
            return copy.deepcopy(rec)
        return None

    def find_active_by_worker(self, worker_urn: str) -> List[WorkerEvaluationRecord]:
        return [copy.deepcopy(r) for r in self._records.values() if r.worker_urn == worker_urn and r.is_active]

    def find_by_session(self, session_id: str) -> List[WorkerEvaluationRecord]:
        return [copy.deepcopy(r) for r in self._records.values() if r.session_id == session_id]

    def list_all(self) -> List[WorkerEvaluationRecord]:
        return [copy.deepcopy(r) for r in self._records.values()]

    def deactivate_old_versions(self, decision_id: str, exclude_version: int) -> None:
        for r in self._records.values():
            if r.decision_id == decision_id and r.evaluation_version != exclude_version and r.is_active:
                r.is_active = False
                r.superseded_by_version = exclude_version

    def deactivate_by_session(self, session_id: str) -> None:
        for r in self._records.values():
            if r.session_id == session_id and r.is_active:
                r.is_active = False
                r.invalidated_by_version = r.evaluation_version + 1

    def clear(self) -> None:
        self._records.clear()


# ==========================================
# 2. File-Based Repositories
# ==========================================

class FilePerformanceSessionRepository(PerformanceSessionRepository):
    def __init__(self, storage_dir: str = ".karsa/performance/sessions/"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, session_id: str) -> str:
        return os.path.join(self.storage_dir, f"{session_id}.json")

    def save(self, session: PerformanceSession) -> None:
        path = self._get_path(session.session_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                existing_data = json.load(f)
            existing = PerformanceSession.from_dict(existing_data)
            if existing.aggregate_version != session.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict on session {session.session_id}: expected version {existing.aggregate_version}, got {session.aggregate_version}"
                )
        with open(path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    def get_by_id(self, session_id: str) -> Optional[PerformanceSession]:
        path = self._get_path(session_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return PerformanceSession.from_dict(data)

    def list_all(self) -> List[PerformanceSession]:
        sessions = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    sessions.append(PerformanceSession.from_dict(data))
                except Exception:
                    pass
        return sessions

    def clear(self) -> None:
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(self.storage_dir, filename))
                except Exception:
                    pass


class FileWorkerEvaluationRepository(WorkerEvaluationRepository):
    def __init__(self, storage_dir: str = ".karsa/performance/records/"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, record_id: str, version: int) -> str:
        return os.path.join(self.storage_dir, f"{record_id}_v{version}.json")

    def save(self, record: WorkerEvaluationRecord) -> None:
        path = self._get_path(record.record_id, record.evaluation_version)
        if os.path.exists(path):
            raise ValueError(f"Performance record already exists: {record.record_id} version {record.evaluation_version}")
        with open(path, "w") as f:
            json.dump(record.to_dict(), f, indent=2)

    def find_by_id(self, record_id: str, version: int) -> Optional[WorkerEvaluationRecord]:
        path = self._get_path(record_id, version)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return WorkerEvaluationRecord.from_dict(data)

    def find_active_by_worker(self, worker_urn: str) -> List[WorkerEvaluationRecord]:
        records = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    rec = WorkerEvaluationRecord.from_dict(data)
                    if rec.worker_urn == worker_urn and rec.is_active:
                        records.append(rec)
                except Exception:
                    pass
        return records

    def find_by_session(self, session_id: str) -> List[WorkerEvaluationRecord]:
        records = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    rec = WorkerEvaluationRecord.from_dict(data)
                    if rec.session_id == session_id:
                        records.append(rec)
                except Exception:
                    pass
        return records

    def list_all(self) -> List[WorkerEvaluationRecord]:
        records = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    records.append(WorkerEvaluationRecord.from_dict(data))
                except Exception:
                    pass
        return records

    def deactivate_old_versions(self, decision_id: str, exclude_version: int) -> None:
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    rec = WorkerEvaluationRecord.from_dict(data)
                    if rec.decision_id == decision_id and rec.evaluation_version != exclude_version and rec.is_active:
                        rec.is_active = False
                        rec.superseded_by_version = exclude_version
                        with open(path, "w") as f:
                            json.dump(rec.to_dict(), f, indent=2)
                except Exception:
                    pass

    def deactivate_by_session(self, session_id: str) -> None:
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    rec = WorkerEvaluationRecord.from_dict(data)
                    if rec.session_id == session_id and rec.is_active:
                        rec.is_active = False
                        rec.invalidated_by_version = rec.evaluation_version + 1
                        with open(path, "w") as f:
                            json.dump(rec.to_dict(), f, indent=2)
                except Exception:
                    pass

    def clear(self) -> None:
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(self.storage_dir, filename))
                except Exception:
                    pass


# ==========================================
# 3. PostgreSQL Repositories
# ==========================================

class PostgresPerformanceSessionRepository(PerformanceSessionRepository):
    def __init__(self, connection):
        self.conn = connection

    def save(self, session: PerformanceSession) -> None:
        cur = self.conn.cursor()
        sid = session.session_id
        
        cur.execute("SELECT aggregate_version FROM performance_sessions WHERE session_id = %s", (sid,))
        row = cur.fetchone()
        
        if not row:
            cur.execute(
                """
                INSERT INTO performance_sessions (
                    session_id, horizon_start, horizon_end, state, raw_input_manifest_hash, aggregate_version
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    sid,
                    session.horizon_start,
                    session.horizon_end,
                    session.state,
                    session.raw_input_manifest_hash,
                    session.aggregate_version
                )
            )
        else:
            existing_ver = row[0]
            if existing_ver != session.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict on session {sid}: expected version {existing_ver}, got {session.aggregate_version}"
                )
            cur.execute(
                """
                UPDATE performance_sessions 
                SET state = %s, raw_input_manifest_hash = %s, aggregate_version = %s
                WHERE session_id = %s AND aggregate_version = %s
                """,
                (
                    session.state,
                    session.raw_input_manifest_hash,
                    session.aggregate_version,
                    sid,
                    existing_ver
                )
            )
            if cur.rowcount == 0:
                raise ConcurrencyConflictError(f"Concurrency update failed on session {sid}")

    def get_by_id(self, session_id: str) -> Optional[PerformanceSession]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT session_id, horizon_start, horizon_end, state, raw_input_manifest_hash, aggregate_version
            FROM performance_sessions WHERE session_id = %s
            """,
            (session_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return PerformanceSession(
            session_id=row[0],
            horizon_start=row[1],
            horizon_end=row[2],
            state=row[3],
            raw_input_manifest_hash=row[4],
            aggregate_version=row[5]
        )

    def list_all(self) -> List[PerformanceSession]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT session_id, horizon_start, horizon_end, state, raw_input_manifest_hash, aggregate_version
            FROM performance_sessions
            """
        )
        sessions = []
        for row in cur.fetchall():
            sessions.append(
                PerformanceSession(
                    session_id=row[0],
                    horizon_start=row[1],
                    horizon_end=row[2],
                    state=row[3],
                    raw_input_manifest_hash=row[4],
                    aggregate_version=row[5]
                )
            )
        return sessions

    def clear(self) -> None:
        cur = self.conn.cursor()
        cur.execute("TRUNCATE TABLE performance_sessions CASCADE;")


class PostgresWorkerEvaluationRepository(WorkerEvaluationRepository):
    def __init__(self, connection):
        self.conn = connection

    def save(self, record: WorkerEvaluationRecord) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT 1 FROM worker_evaluation_records WHERE record_id = %s AND evaluation_version = %s",
            (record.record_id, record.evaluation_version)
        )
        if cur.fetchone():
            raise ValueError(f"Worker evaluation record already exists: {record.record_id} version {record.evaluation_version}")

        cur.execute(
            """
            INSERT INTO worker_evaluation_records (
                record_id, session_id, decision_id, worker_urn, asset_urn, regime_urn,
                forecast_probability, realized_outcome, brier_score_component, realized_return,
                evaluation_version, is_active, superseded_by_version, invalidated_by_version,
                calculated_at, aggregate_version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record.record_id,
                record.session_id,
                record.decision_id,
                record.worker_urn,
                record.asset_urn,
                record.regime_urn,
                record.forecast_probability,
                record.realized_outcome,
                record.brier_score_component,
                record.realized_return,
                record.evaluation_version,
                record.is_active,
                record.superseded_by_version,
                record.invalidated_by_version,
                record.calculated_at,
                record.aggregate_version
            )
        )

    def find_by_id(self, record_id: str, version: int) -> Optional[WorkerEvaluationRecord]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT record_id, session_id, decision_id, worker_urn, asset_urn, regime_urn,
                   forecast_probability, realized_outcome, brier_score_component, realized_return,
                   evaluation_version, is_active, superseded_by_version, invalidated_by_version,
                   calculated_at, aggregate_version
            FROM worker_evaluation_records WHERE record_id = %s AND evaluation_version = %s
            """,
            (record_id, version)
        )
        row = cur.fetchone()
        if not row:
            return None
        return WorkerEvaluationRecord(
            record_id=row[0],
            session_id=row[1],
            decision_id=row[2],
            worker_urn=row[3],
            asset_urn=row[4],
            regime_urn=row[5],
            forecast_probability=row[6],
            realized_outcome=row[7],
            brier_score_component=row[8],
            realized_return=row[9],
            evaluation_version=row[10],
            is_active=row[11],
            calculated_at=row[14],
            superseded_by_version=row[12],
            invalidated_by_version=row[13],
            aggregate_version=row[15]
        )

    def find_active_by_worker(self, worker_urn: str) -> List[WorkerEvaluationRecord]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT record_id, session_id, decision_id, worker_urn, asset_urn, regime_urn,
                   forecast_probability, realized_outcome, brier_score_component, realized_return,
                   evaluation_version, is_active, superseded_by_version, invalidated_by_version,
                   calculated_at, aggregate_version
            FROM worker_evaluation_records WHERE worker_urn = %s AND is_active = TRUE
            """,
            (worker_urn,)
        )
        records = []
        for row in cur.fetchall():
            records.append(
                WorkerEvaluationRecord(
                    record_id=row[0],
                    session_id=row[1],
                    decision_id=row[2],
                    worker_urn=row[3],
                    asset_urn=row[4],
                    regime_urn=row[5],
                    forecast_probability=row[6],
                    realized_outcome=row[7],
                    brier_score_component=row[8],
                    realized_return=row[9],
                    evaluation_version=row[10],
                    is_active=row[11],
                    calculated_at=row[14],
                    superseded_by_version=row[12],
                    invalidated_by_version=row[13],
                    aggregate_version=row[15]
                )
            )
        return records

    def find_by_session(self, session_id: str) -> List[WorkerEvaluationRecord]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT record_id, session_id, decision_id, worker_urn, asset_urn, regime_urn,
                   forecast_probability, realized_outcome, brier_score_component, realized_return,
                   evaluation_version, is_active, superseded_by_version, invalidated_by_version,
                   calculated_at, aggregate_version
            FROM worker_evaluation_records WHERE session_id = %s
            """,
            (session_id,)
        )
        records = []
        for row in cur.fetchall():
            records.append(
                WorkerEvaluationRecord(
                    record_id=row[0],
                    session_id=row[1],
                    decision_id=row[2],
                    worker_urn=row[3],
                    asset_urn=row[4],
                    regime_urn=row[5],
                    forecast_probability=row[6],
                    realized_outcome=row[7],
                    brier_score_component=row[8],
                    realized_return=row[9],
                    evaluation_version=row[10],
                    is_active=row[11],
                    calculated_at=row[14],
                    superseded_by_version=row[12],
                    invalidated_by_version=row[13],
                    aggregate_version=row[15]
                )
            )
        return records

    def list_all(self) -> List[WorkerEvaluationRecord]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT record_id, session_id, decision_id, worker_urn, asset_urn, regime_urn,
                   forecast_probability, realized_outcome, brier_score_component, realized_return,
                   evaluation_version, is_active, superseded_by_version, invalidated_by_version,
                   calculated_at, aggregate_version
            FROM worker_evaluation_records
            """
        )
        records = []
        for row in cur.fetchall():
            records.append(
                WorkerEvaluationRecord(
                    record_id=row[0],
                    session_id=row[1],
                    decision_id=row[2],
                    worker_urn=row[3],
                    asset_urn=row[4],
                    regime_urn=row[5],
                    forecast_probability=row[6],
                    realized_outcome=row[7],
                    brier_score_component=row[8],
                    realized_return=row[9],
                    evaluation_version=row[10],
                    is_active=row[11],
                    calculated_at=row[14],
                    superseded_by_version=row[12],
                    invalidated_by_version=row[13],
                    aggregate_version=row[15]
                )
            )
        return records

    def deactivate_old_versions(self, decision_id: str, exclude_version: int) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE worker_evaluation_records
            SET is_active = FALSE, superseded_by_version = %s, aggregate_version = aggregate_version + 1
            WHERE decision_id = %s AND evaluation_version != %s AND is_active = TRUE
            """,
            (exclude_version, decision_id, exclude_version)
        )

    def deactivate_by_session(self, session_id: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE worker_evaluation_records
            SET is_active = FALSE, invalidated_by_version = evaluation_version + 1, aggregate_version = aggregate_version + 1
            WHERE session_id = %s AND is_active = TRUE
            """,
            (session_id,)
        )

    def clear(self) -> None:
        cur = self.conn.cursor()
        cur.execute("TRUNCATE TABLE worker_evaluation_records CASCADE;")
