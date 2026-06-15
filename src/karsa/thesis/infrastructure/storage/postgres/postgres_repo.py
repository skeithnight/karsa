import psycopg2
import json
from typing import Any
from typing import List, Optional
from karsa.thesis.domain.models import (
    Thesis, ThesisSnapshot, ThesisTransition, ThesisDelta,
    ThesisAssumptionIdentity, ThesisAssumptionVersion
)
from karsa.thesis.domain.value_objects import LifecycleState, AssumptionLifecycleState, CalibrationReference
from karsa.thesis.domain.repository.repositories import (
    ThesisRepository, ThesisSnapshotRepository, ThesisTransitionRepository,
    AssumptionIdentityRepository, AssumptionVersionRepository,
    ConcurrencyDriftError, ImmutableMutationError, LineageCycleError
)

class PostgresThesisRepository(ThesisRepository):
    def __init__(self, conn: Any):
        self.conn = conn

    def save(self, thesis: Thesis) -> None:
        c = self.conn.cursor()
        if thesis.aggregate_version == 1:
            try:
                c.execute(
                    "INSERT INTO theses (thesis_urn, current_snapshot_urn, current_status, aggregate_version) VALUES (%s, %s, %s, %s)",
                    (thesis.thesis_urn, thesis.current_snapshot_urn, thesis.current_status.value, thesis.aggregate_version)
                )
            except psycopg2.IntegrityError:
                raise ConcurrencyDriftError()
        else:
            expected_v = thesis.aggregate_version - 1
            c.execute(
                "UPDATE theses SET current_snapshot_urn=%s, current_status=%s, aggregate_version=%s WHERE thesis_urn=%s AND aggregate_version=%s",
                (thesis.current_snapshot_urn, thesis.current_status.value, thesis.aggregate_version, thesis.thesis_urn, expected_v)
            )
            if c.rowcount == 0:
                raise ConcurrencyDriftError()

    def get_by_urn(self, urn: str) -> Optional[Thesis]:
        c = self.conn.cursor()
        c.execute("SELECT thesis_urn, current_snapshot_urn, current_status, aggregate_version FROM theses WHERE thesis_urn = %s", (urn,))
        row = c.fetchone()
        if not row:
            return None
        return Thesis(row[0], row[1], LifecycleState(row[2]), row[3])

    def list_active(self, limit: int, last_urn: Optional[str] = None) -> List[Thesis]:
        c = self.conn.cursor()
        if last_urn:
            c.execute("SELECT thesis_urn, current_snapshot_urn, current_status, aggregate_version FROM theses WHERE current_status = 'ACTIVE' AND thesis_urn > %s ORDER BY thesis_urn LIMIT %s", (last_urn, limit))
        else:
            c.execute("SELECT thesis_urn, current_snapshot_urn, current_status, aggregate_version FROM theses WHERE current_status = 'ACTIVE' ORDER BY thesis_urn LIMIT %s", (limit,))
        
        return [Thesis(row[0], row[1], LifecycleState(row[2]), row[3]) for row in c.fetchall()]

class PostgresThesisSnapshotRepository(ThesisSnapshotRepository):
    def __init__(self, conn: Any):
        self.conn = conn

    def save(self, snapshot: ThesisSnapshot) -> None:
        c = self.conn.cursor()
        c.execute("SELECT 1 FROM thesis_snapshots WHERE snapshot_urn = %s", (snapshot.snapshot_urn,))
        if c.fetchone():
            raise ImmutableMutationError()
            
        c.execute(
            "INSERT INTO thesis_snapshots (snapshot_urn, snapshot_version, lifecycle_state, origin_regime_snapshot_urn, supersedes_snapshot_urn, invalidates_snapshot_urn) VALUES (%s, %s, %s, %s, %s, %s)",
            (snapshot.snapshot_urn, snapshot.snapshot_version, snapshot.lifecycle_state.value, snapshot.origin_regime_snapshot_urn, snapshot.supersedes_snapshot_urn, snapshot.invalidates_snapshot_urn)
        )

    def get_by_urn(self, urn: str) -> Optional[ThesisSnapshot]:
        c = self.conn.cursor()
        c.execute("SELECT snapshot_urn, snapshot_version, lifecycle_state, origin_regime_snapshot_urn, supersedes_snapshot_urn, invalidates_snapshot_urn FROM thesis_snapshots WHERE snapshot_urn = %s", (urn,))
        row = c.fetchone()
        if not row:
            return None
        return ThesisSnapshot(row[0], row[1], LifecycleState(row[2]), row[3], row[4], row[5], [])

    def fetch_snapshot_lineage(self, snapshot_urn: str) -> List[ThesisSnapshot]:
        c = self.conn.cursor()
        c.execute("""
            WITH RECURSIVE lineage AS (
                SELECT snapshot_urn, snapshot_version, lifecycle_state, origin_regime_snapshot_urn, supersedes_snapshot_urn, invalidates_snapshot_urn, 1 as depth
                FROM thesis_snapshots WHERE snapshot_urn = %s
                UNION ALL
                SELECT s.snapshot_urn, s.snapshot_version, s.lifecycle_state, s.origin_regime_snapshot_urn, s.supersedes_snapshot_urn, s.invalidates_snapshot_urn, l.depth + 1
                FROM thesis_snapshots s
                INNER JOIN lineage l ON s.snapshot_urn = l.supersedes_snapshot_urn WHERE l.depth < 100
            )
            SELECT * FROM lineage ORDER BY depth
        """, (snapshot_urn,))
        
        results = c.fetchall()
        visited = set()
        out = []
        for row in results:
            if row[0] in visited:
                raise LineageCycleError()
            visited.add(row[0])
            out.append(ThesisSnapshot(row[0], row[1], LifecycleState(row[2]), row[3], row[4], row[5], []))
            
        return out

class PostgresThesisTransitionRepository(ThesisTransitionRepository):
    def __init__(self, conn: Any):
        self.conn = conn

    def save(self, transition: ThesisTransition) -> None:
        c = self.conn.cursor()
        c.execute("SELECT 1 FROM thesis_transitions WHERE transition_urn = %s", (transition.transition_urn,))
        if c.fetchone():
            raise ImmutableMutationError()
            
        c.execute(
            "INSERT INTO thesis_transitions (transition_urn, supersedes_transition_urn, invalidates_transition_urn, delta_urn, delta_manifest_hash, added_assumptions, removed_assumptions) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (transition.transition_urn, transition.supersedes_transition_urn, transition.invalidates_transition_urn, transition.delta.delta_urn, transition.delta.delta_manifest_hash, json.dumps(transition.delta.added_assumptions), json.dumps(transition.delta.removed_assumptions))
        )

    def get_by_urn(self, urn: str) -> Optional[ThesisTransition]:
        c = self.conn.cursor()
        c.execute("SELECT transition_urn, supersedes_transition_urn, invalidates_transition_urn, delta_urn, delta_manifest_hash, added_assumptions, removed_assumptions FROM thesis_transitions WHERE transition_urn = %s", (urn,))
        row = c.fetchone()
        if not row:
            return None
        delta = ThesisDelta(row[3], row[4], row[5], row[6])
        return ThesisTransition(row[0], row[1], row[2], delta)

    def fetch_transition_lineage(self, transition_urn: str) -> List[ThesisTransition]:
        c = self.conn.cursor()
        c.execute("""
            WITH RECURSIVE lineage AS (
                SELECT transition_urn, supersedes_transition_urn, invalidates_transition_urn, delta_urn, delta_manifest_hash, added_assumptions, removed_assumptions, 1 as depth
                FROM thesis_transitions WHERE transition_urn = %s
                UNION ALL
                SELECT t.transition_urn, t.supersedes_transition_urn, t.invalidates_transition_urn, t.delta_urn, t.delta_manifest_hash, t.added_assumptions, t.removed_assumptions, l.depth + 1
                FROM thesis_transitions t
                INNER JOIN lineage l ON t.transition_urn = l.supersedes_transition_urn WHERE l.depth < 100
            )
            SELECT * FROM lineage ORDER BY depth
        """, (transition_urn,))
        
        results = c.fetchall()
        visited = set()
        out = []
        for row in results:
            if row[0] in visited:
                raise LineageCycleError()
            visited.add(row[0])
            delta = ThesisDelta(row[3], row[4], row[5], row[6])
            out.append(ThesisTransition(row[0], row[1], row[2], delta))
            
        return out

class PostgresAssumptionIdentityRepository(AssumptionIdentityRepository):
    def __init__(self, conn: Any):
        self.conn = conn

    def save(self, identity: ThesisAssumptionIdentity) -> None:
        c = self.conn.cursor()
        c.execute("INSERT INTO thesis_assumption_identities (assumption_urn) VALUES (%s) ON CONFLICT (assumption_urn) DO NOTHING", (identity.assumption_urn,))

    def get_by_urn(self, urn: str) -> Optional[ThesisAssumptionIdentity]:
        c = self.conn.cursor()
        c.execute("SELECT assumption_urn FROM thesis_assumption_identities WHERE assumption_urn = %s", (urn,))
        row = c.fetchone()
        return ThesisAssumptionIdentity(row[0]) if row else None

class PostgresAssumptionVersionRepository(AssumptionVersionRepository):
    def __init__(self, conn: Any):
        self.conn = conn

    def save(self, version: ThesisAssumptionVersion) -> None:
        c = self.conn.cursor()
        c.execute("SELECT 1 FROM thesis_assumption_versions WHERE assumption_urn = %s AND assumption_version = %s", (version.assumption_urn, version.assumption_version))
        if c.fetchone():
            raise ImmutableMutationError()
        
        cal_urn = version.calibrated_confidence_reference.calibration_urn if version.calibrated_confidence_reference else None
        cal_hash = version.calibrated_confidence_reference.calibration_manifest_hash if version.calibrated_confidence_reference else None
        
        c.execute("""
            INSERT INTO thesis_assumption_versions 
            (assumption_urn, assumption_version, assumption_statement, raw_confidence, lifecycle_state, assumption_manifest_hash, cal_urn, cal_hash) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (version.assumption_urn, version.assumption_version, version.assumption_statement, version.raw_confidence, version.lifecycle_state.value, version.assumption_manifest_hash, cal_urn, cal_hash))

    def get_by_urn_and_version(self, urn: str, version: int) -> Optional[ThesisAssumptionVersion]:
        c = self.conn.cursor()
        c.execute("SELECT assumption_urn, assumption_version, assumption_statement, raw_confidence, lifecycle_state, assumption_manifest_hash, cal_urn, cal_hash FROM thesis_assumption_versions WHERE assumption_urn = %s AND assumption_version = %s", (urn, version))
        row = c.fetchone()
        if not row:
            return None
            
        cal_ref = CalibrationReference(row[6], row[7]) if row[6] else None
        return ThesisAssumptionVersion(row[0], row[1], row[2], row[3], AssumptionLifecycleState(row[4]), row[5], cal_ref)
