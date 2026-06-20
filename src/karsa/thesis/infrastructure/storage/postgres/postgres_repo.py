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

    def __init__(self, conn: Any):
        self.conn = conn

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

    def __init__(self, conn: Any):
        self.conn = conn

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

    def __init__(self, conn: Any):
        self.conn = conn

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

    def __init__(self, conn: Any):
        self.conn = conn

    def get_by_urn(self, urn: str) -> Optional[ThesisAssumptionIdentity]:
        c = self.conn.cursor()
        c.execute("SELECT assumption_urn FROM thesis_assumption_identities WHERE assumption_urn = %s", (urn,))
        row = c.fetchone()
        return ThesisAssumptionIdentity(row[0]) if row else None

class PostgresAssumptionVersionRepository(AssumptionVersionRepository):
    def __init__(self, conn: Any):
        self.conn = conn

    def __init__(self, conn: Any):
        self.conn = conn

    def get_by_urn_and_version(self, urn: str, version: int) -> Optional[ThesisAssumptionVersion]:
        c = self.conn.cursor()
        c.execute("SELECT assumption_urn, assumption_version, assumption_statement, raw_confidence, lifecycle_state, assumption_manifest_hash, cal_urn, cal_hash FROM thesis_assumption_versions WHERE assumption_urn = %s AND assumption_version = %s", (urn, version))
        row = c.fetchone()
        if not row:
            return None
            
        cal_ref = CalibrationReference(row[6], row[7]) if row[6] else None
        return ThesisAssumptionVersion(row[0], row[1], row[2], row[3], AssumptionLifecycleState(row[4]), row[5], cal_ref)

class PostgresThesisReadRepository:
    def __init__(self, pool):
        self.pool = pool

    def get_all(self, limit: int = 50, offset: int = 0):
        from karsa.thesis.api.dtos import ThesisSummaryDto
        with self.pool.getconn() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT thesis_urn, title, lifecycle_state, snapshot_version, confidence, author_urn, regime_urn 
                FROM thesis_snapshots 
                WHERE thesis_urn IS NOT NULL
                ORDER BY thesis_urn DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
            rows = c.fetchall()
            self.pool.putconn(conn)
            results = []
            for r in rows:
                if r[0]:
                    results.append(ThesisSummaryDto(
                        urn=r[0], title=r[1] or "", status=r[2], version=r[3],
                        confidence=float(r[4] or 0.0), author_urn=r[5] or "", regime_urn=r[6] or ""
                    ))
            return results

    def get_by_urn(self, urn: str):
        from karsa.thesis.api.dtos import ThesisDetailDto
        with self.pool.getconn() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT thesis_urn, snapshot_urn, title, summary, rationale, 
                       confidence, author_urn, regime_urn, lifecycle_state, 
                       snapshot_version, assumptions_jsonb
                FROM thesis_snapshots 
                WHERE thesis_urn = %s LIMIT 1
            """, (urn,))
            row = c.fetchone()
            self.pool.putconn(conn)
            if not row: return None
            return ThesisDetailDto(
                urn=row[0], current_snapshot_urn=row[1], title=row[2] or "",
                summary=row[3] or "", rationale=row[4] or "", confidence=float(row[5] or 0.0),
                author_urn=row[6] or "", regime_urn=row[7] or "", status=row[8],
                version=row[9], assumptions=row[10] if row[10] else []
            )
