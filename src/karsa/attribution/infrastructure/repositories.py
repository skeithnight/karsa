import os
import json
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict
from karsa.attribution.domain.model.models import AttributionSession, PerformanceAttributionRecord
from karsa.attribution.domain.model.repositories import AttributionSessionRepository, PerformanceAttributionRepository
from karsa.shared.infrastructure.uow import ConcurrencyConflictError

# ==========================================
# 1. InMemory Repositories
# ==========================================

import copy

class InMemoryAttributionSessionRepository(AttributionSessionRepository):
    def __init__(self):
        self._sessions: Dict[str, AttributionSession] = {}

    def save(self, session: AttributionSession) -> None:
        sid = session.session_id
        if sid in self._sessions:
            existing = self._sessions[sid]
            # OCC check
            if existing.aggregate_version != session.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict on session {sid}: expected version {existing.aggregate_version}, got {session.aggregate_version}"
                )
        self._sessions[sid] = copy.deepcopy(session)

    def get_by_id(self, session_id: str) -> Optional[AttributionSession]:
        session = self._sessions.get(session_id)
        if session:
            return copy.deepcopy(session)
        return None

    def list_all(self) -> List[AttributionSession]:
        return [copy.deepcopy(s) for s in self._sessions.values()]

    def clear(self) -> None:
        self._sessions.clear()


class InMemoryPerformanceAttributionRepository(PerformanceAttributionRepository):
    def __init__(self):
        self._records: Dict[str, PerformanceAttributionRecord] = {}

    def save(self, record: PerformanceAttributionRecord) -> None:
        rid = record.record_id
        ver = record.attribution_version
        key = f"{rid}:{ver}"
        
        if key in self._records:
            raise ValueError(f"Performance attribution record already exists: {key}")
            
        self._records[key] = copy.deepcopy(record)

    def find_by_id(self, record_id: str, version: int) -> Optional[PerformanceAttributionRecord]:
        rec = self._records.get(f"{record_id}:{version}")
        if rec:
            return copy.deepcopy(rec)
        return None

    def find_active_by_decision(self, decision_id: str) -> List[PerformanceAttributionRecord]:
        active_records = []
        for r in self._records.values():
            if r.decision_id == decision_id and r.is_active:
                active_records.append(copy.deepcopy(r))
        return active_records

    def find_by_session(self, session_id: str) -> List[PerformanceAttributionRecord]:
        session_records = []
        for r in self._records.values():
            if r.session_id == session_id:
                session_records.append(copy.deepcopy(r))
        return session_records

    def list_all(self) -> List[PerformanceAttributionRecord]:
        return [copy.deepcopy(r) for r in self._records.values()]

    def deactivate_old_versions(self, decision_id: str, exclude_version: int) -> None:
        for r in self._records.values():
            if r.decision_id == decision_id and r.attribution_version != exclude_version and r.is_active:
                r.is_active = False

    def deactivate_by_session(self, session_id: str) -> None:
        for r in self._records.values():
            if r.session_id == session_id and r.is_active:
                r.is_active = False

    def clear(self) -> None:
        self._records.clear()


# ==========================================
# 2. File-Based Repositories
# ==========================================

class FileAttributionSessionRepository(AttributionSessionRepository):
    def __init__(self, storage_dir: str = ".karsa/attribution/sessions/"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, session_id: str) -> str:
        return os.path.join(self.storage_dir, f"{session_id}.json")

    def save(self, session: AttributionSession) -> None:
        path = self._get_path(session.session_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                existing_data = json.load(f)
            existing = AttributionSession.from_dict(existing_data)
            # OCC check
            if existing.aggregate_version != session.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict on session {session.session_id}: expected version {existing.aggregate_version}, got {session.aggregate_version}"
                )
        with open(path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    def get_by_id(self, session_id: str) -> Optional[AttributionSession]:
        path = self._get_path(session_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return AttributionSession.from_dict(data)

    def list_all(self) -> List[AttributionSession]:
        sessions = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    sessions.append(AttributionSession.from_dict(data))
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


class FilePerformanceAttributionRepository(PerformanceAttributionRepository):
    def __init__(self, storage_dir: str = ".karsa/attribution/records/"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, record_id: str, version: int) -> str:
        return os.path.join(self.storage_dir, f"{record_id}_v{version}.json")

    def save(self, record: PerformanceAttributionRecord) -> None:
        path = self._get_path(record.record_id, record.attribution_version)
        if os.path.exists(path):
            raise ValueError(f"Performance record already exists: {record.record_id} version {record.attribution_version}")
        with open(path, "w") as f:
            json.dump(record.to_dict(), f, indent=2)

    def find_by_id(self, record_id: str, version: int) -> Optional[PerformanceAttributionRecord]:
        path = self._get_path(record_id, version)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return PerformanceAttributionRecord.from_dict(data)

    def find_active_by_decision(self, decision_id: str) -> List[PerformanceAttributionRecord]:
        active_records = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    rec = PerformanceAttributionRecord.from_dict(data)
                    if rec.decision_id == decision_id and rec.is_active:
                        active_records.append(rec)
                except Exception:
                    pass
        return active_records

    def find_by_session(self, session_id: str) -> List[PerformanceAttributionRecord]:
        session_records = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    rec = PerformanceAttributionRecord.from_dict(data)
                    if rec.session_id == session_id:
                        session_records.append(rec)
                except Exception:
                    pass
        return session_records

    def list_all(self) -> List[PerformanceAttributionRecord]:
        records = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    records.append(PerformanceAttributionRecord.from_dict(data))
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
                    rec = PerformanceAttributionRecord.from_dict(data)
                    if rec.decision_id == decision_id and rec.attribution_version != exclude_version and rec.is_active:
                        rec.is_active = False
                        # Resave updated active flag
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
                    rec = PerformanceAttributionRecord.from_dict(data)
                    if rec.session_id == session_id and rec.is_active:
                        rec.is_active = False
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

class PostgresAttributionSessionRepository(AttributionSessionRepository):
    def __init__(self, connection):
        self.conn = connection

    def save(self, session: AttributionSession) -> None:
        cur = self.conn.cursor()
        sid = session.session_id
        
        # Check existence and version for OCC
        cur.execute("SELECT aggregate_version FROM attribution_sessions WHERE session_id = %s", (sid,))
        row = cur.fetchone()
        
        if not row:
            # Insert new
            cur.execute(
                """
                INSERT INTO attribution_sessions (
                    session_id, horizon_start, horizon_end, state, 
                    compounding_strategy, raw_input_manifest_hash, aggregate_version
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    sid,
                    session.horizon_start,
                    session.horizon_end,
                    session.state,
                    session.compounding_strategy,
                    session.raw_input_manifest_hash,
                    session.aggregate_version
                )
            )
        else:
            # Update with OCC version constraint
            existing_ver = row[0]
            if existing_ver != session.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict on session {sid}: expected version {existing_ver}, got {session.aggregate_version}"
                )
                
            cur.execute(
                """
                UPDATE attribution_sessions 
                SET state = %s, compounding_strategy = %s, raw_input_manifest_hash = %s, aggregate_version = %s
                WHERE session_id = %s AND aggregate_version = %s
                """,
                (
                    session.state,
                    session.compounding_strategy,
                    session.raw_input_manifest_hash,
                    session.aggregate_version,
                    sid,
                    existing_ver
                )
            )
            if cur.rowcount == 0:
                raise ConcurrencyConflictError(f"Concurrency update failed on session {sid}")

    def get_by_id(self, session_id: str) -> Optional[AttributionSession]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT session_id, horizon_start, horizon_end, state, 
                   compounding_strategy, raw_input_manifest_hash, aggregate_version
            FROM attribution_sessions WHERE session_id = %s
            """,
            (session_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return AttributionSession(
            session_id=row[0],
            horizon_start=row[1],
            horizon_end=row[2],
            state=row[3],
            compounding_strategy=row[4],
            raw_input_manifest_hash=row[5],
            aggregate_version=row[6]
        )

    def list_all(self) -> List[AttributionSession]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT session_id, horizon_start, horizon_end, state, 
                   compounding_strategy, raw_input_manifest_hash, aggregate_version
            FROM attribution_sessions
            """
        )
        sessions = []
        for row in cur.fetchall():
            sessions.append(
                AttributionSession(
                    session_id=row[0],
                    horizon_start=row[1],
                    horizon_end=row[2],
                    state=row[3],
                    compounding_strategy=row[4],
                    raw_input_manifest_hash=row[5],
                    aggregate_version=row[6]
                )
            )
        return sessions

    def clear(self) -> None:
        cur = self.conn.cursor()
        cur.execute("TRUNCATE TABLE attribution_sessions CASCADE;")


class PostgresPerformanceAttributionRepository(PerformanceAttributionRepository):
    def __init__(self, connection):
        self.conn = connection

    def save(self, record: PerformanceAttributionRecord) -> None:
        cur = self.conn.cursor()
        # Verify first if version exists
        cur.execute(
            "SELECT 1 FROM performance_attribution_records WHERE record_id = %s AND attribution_version = %s",
            (record.record_id, record.attribution_version)
        )
        if cur.fetchone():
            raise ValueError(f"Performance attribution record version already exists: {record.record_id} version {record.attribution_version}")
            
        cur.execute(
            """
            INSERT INTO performance_attribution_records (
                record_id, session_id, decision_id, thesis_urn, worker_urn, capability_urn,
                regime_urn, asset_urn, selection_return, allocation_return, execution_return,
                beta_return, liquidation_tracking_residual, attribution_version, is_active,
                calculated_at, aggregate_version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record.record_id,
                record.session_id,
                record.decision_id,
                record.thesis_urn,
                record.worker_urn,
                record.capability_urn,
                record.regime_urn,
                record.asset_urn,
                record.selection_return,
                record.allocation_return,
                record.execution_return,
                record.beta_return,
                record.liquidation_tracking_residual,
                record.attribution_version,
                record.is_active,
                record.calculated_at,
                record.aggregate_version
            )
        )

    def find_by_id(self, record_id: str, version: int) -> Optional[PerformanceAttributionRecord]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT record_id, session_id, decision_id, thesis_urn, worker_urn, capability_urn,
                   regime_urn, asset_urn, selection_return, allocation_return, execution_return,
                   beta_return, liquidation_tracking_residual, attribution_version, is_active,
                   calculated_at, aggregate_version
            FROM performance_attribution_records
            WHERE record_id = %s AND attribution_version = %s
            """,
            (record_id, version)
        )
        row = cur.fetchone()
        if not row:
            return None
        return PerformanceAttributionRecord(
            record_id=row[0],
            session_id=row[1],
            decision_id=row[2],
            thesis_urn=row[3],
            worker_urn=row[4],
            capability_urn=row[5],
            regime_urn=row[6],
            asset_urn=row[7],
            selection_return=row[8],
            allocation_return=row[9],
            execution_return=row[10],
            beta_return=row[11],
            liquidation_tracking_residual=row[12],
            attribution_version=row[13],
            is_active=row[14],
            calculated_at=row[15],
            aggregate_version=row[16]
        )

    def find_active_by_decision(self, decision_id: str) -> List[PerformanceAttributionRecord]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT record_id, session_id, decision_id, thesis_urn, worker_urn, capability_urn,
                   regime_urn, asset_urn, selection_return, allocation_return, execution_return,
                   beta_return, liquidation_tracking_residual, attribution_version, is_active,
                   calculated_at, aggregate_version
            FROM performance_attribution_records
            WHERE decision_id = %s AND is_active = TRUE
            """,
            (decision_id,)
        )
        records = []
        for row in cur.fetchall():
            records.append(
                PerformanceAttributionRecord(
                    record_id=row[0],
                    session_id=row[1],
                    decision_id=row[2],
                    thesis_urn=row[3],
                    worker_urn=row[4],
                    capability_urn=row[5],
                    regime_urn=row[6],
                    asset_urn=row[7],
                    selection_return=row[8],
                    allocation_return=row[9],
                    execution_return=row[10],
                    beta_return=row[11],
                    liquidation_tracking_residual=row[12],
                    attribution_version=row[13],
                    is_active=row[14],
                    calculated_at=row[15],
                    aggregate_version=row[16]
                )
            )
        return records

    def find_by_session(self, session_id: str) -> List[PerformanceAttributionRecord]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT record_id, session_id, decision_id, thesis_urn, worker_urn, capability_urn,
                   regime_urn, asset_urn, selection_return, allocation_return, execution_return,
                   beta_return, liquidation_tracking_residual, attribution_version, is_active,
                   calculated_at, aggregate_version
            FROM performance_attribution_records
            WHERE session_id = %s
            """,
            (session_id,)
        )
        records = []
        for row in cur.fetchall():
            records.append(
                PerformanceAttributionRecord(
                    record_id=row[0],
                    session_id=row[1],
                    decision_id=row[2],
                    thesis_urn=row[3],
                    worker_urn=row[4],
                    capability_urn=row[5],
                    regime_urn=row[6],
                    asset_urn=row[7],
                    selection_return=row[8],
                    allocation_return=row[9],
                    execution_return=row[10],
                    beta_return=row[11],
                    liquidation_tracking_residual=row[12],
                    attribution_version=row[13],
                    is_active=row[14],
                    calculated_at=row[15],
                    aggregate_version=row[16]
                )
            )
        return records

    def list_all(self) -> List[PerformanceAttributionRecord]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT record_id, session_id, decision_id, thesis_urn, worker_urn, capability_urn,
                   regime_urn, asset_urn, selection_return, allocation_return, execution_return,
                   beta_return, liquidation_tracking_residual, attribution_version, is_active,
                   calculated_at, aggregate_version
            FROM performance_attribution_records
            """
        )
        records = []
        for row in cur.fetchall():
            records.append(
                PerformanceAttributionRecord(
                    record_id=row[0],
                    session_id=row[1],
                    decision_id=row[2],
                    thesis_urn=row[3],
                    worker_urn=row[4],
                    capability_urn=row[5],
                    regime_urn=row[6],
                    asset_urn=row[7],
                    selection_return=row[8],
                    allocation_return=row[9],
                    execution_return=row[10],
                    beta_return=row[11],
                    liquidation_tracking_residual=row[12],
                    attribution_version=row[13],
                    is_active=row[14],
                    calculated_at=row[15],
                    aggregate_version=row[16]
                )
            )
        return records

    def deactivate_old_versions(self, decision_id: str, exclude_version: int) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE performance_attribution_records
            SET is_active = FALSE, aggregate_version = aggregate_version + 1
            WHERE decision_id = %s AND attribution_version != %s AND is_active = TRUE
            """,
            (decision_id, exclude_version)
        )

    def deactivate_by_session(self, session_id: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE performance_attribution_records
            SET is_active = FALSE, aggregate_version = aggregate_version + 1
            WHERE session_id = %s AND is_active = TRUE
            """,
            (session_id,)
        )

    def clear(self) -> None:
        cur = self.conn.cursor()
        cur.execute("TRUNCATE TABLE performance_attribution_records CASCADE;")
