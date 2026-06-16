import psycopg2
import pytest
from karsa.thesis.domain.models import (
    Thesis, ThesisSnapshot, ThesisTransition, ThesisDelta,
    ThesisAssumptionIdentity, ThesisAssumptionVersion
)
from karsa.thesis.domain.value_objects import LifecycleState, AssumptionLifecycleState
from karsa.thesis.domain.repository.repositories import (
    ConcurrencyDriftError, ImmutableMutationError, LineageCycleError
)
from karsa.thesis.infrastructure.storage.postgres.postgres_repo import (
    PostgresThesisRepository, PostgresThesisSnapshotRepository, PostgresThesisTransitionRepository,
    PostgresAssumptionIdentityRepository, PostgresAssumptionVersionRepository
)

@pytest.fixture
def conn():
    import os
    db_name = os.environ.get("POSTGRES_DB", "postgres")
    db_user = os.environ.get("POSTGRES_USER", "postgres")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "postgres")
    db_host = os.environ.get("POSTGRES_HOST", "localhost")
    db_port = int(os.environ.get("POSTGRES_PORT", 5433))
    connection = psycopg2.connect(dbname=db_name, user=db_user, password=db_pass, host=db_host, port=db_port)
    connection.autocommit = True
    c = connection.cursor()
    
    # Teardown any existing
    c.execute("DROP TABLE IF EXISTS theses CASCADE")
    c.execute("DROP TABLE IF EXISTS thesis_snapshots CASCADE")
    c.execute("DROP TABLE IF EXISTS thesis_transitions CASCADE")
    c.execute("DROP TABLE IF EXISTS thesis_assumption_identities CASCADE")
    c.execute("DROP TABLE IF EXISTS thesis_assumption_versions CASCADE")
    
    # Create tables
    c.execute("""
        CREATE TABLE theses (
            thesis_urn TEXT PRIMARY KEY,
            current_snapshot_urn TEXT,
            current_status TEXT,
            aggregate_version INTEGER
        )
    """)
    c.execute("CREATE INDEX idx_theses_status ON theses (current_status, thesis_urn)")
    
    c.execute("""
        CREATE TABLE thesis_snapshots (
            snapshot_urn TEXT PRIMARY KEY,
            snapshot_version INTEGER,
            lifecycle_state TEXT,
            origin_regime_snapshot_urn TEXT,
            supersedes_snapshot_urn TEXT,
            invalidates_snapshot_urn TEXT
        )
    """)
    c.execute("CREATE INDEX idx_snapshots_supersedes ON thesis_snapshots (supersedes_snapshot_urn)")

    c.execute("""
        CREATE TABLE thesis_transitions (
            transition_urn TEXT PRIMARY KEY,
            supersedes_transition_urn TEXT,
            invalidates_transition_urn TEXT,
            delta_urn TEXT,
            delta_manifest_hash TEXT,
            added_assumptions JSONB,
            removed_assumptions JSONB
        )
    """)
    c.execute("CREATE INDEX idx_transitions_supersedes ON thesis_transitions (supersedes_transition_urn)")

    c.execute("""
        CREATE TABLE thesis_assumption_identities (
            assumption_urn TEXT PRIMARY KEY
        )
    """)
    c.execute("""
        CREATE TABLE thesis_assumption_versions (
            assumption_urn TEXT,
            assumption_version INTEGER,
            assumption_statement TEXT,
            raw_confidence REAL,
            lifecycle_state TEXT,
            assumption_manifest_hash TEXT,
            cal_urn TEXT,
            cal_hash TEXT,
            PRIMARY KEY (assumption_urn, assumption_version)
        )
    """)
    yield connection
    connection.close()

def test_occ_successful_update(conn):
    repo = PostgresThesisRepository(conn)
    t = Thesis("urn1", "s1", LifecycleState.PROPOSED, 1)
    repo.save(t)
    
    t2 = Thesis("urn1", "s2", LifecycleState.ACTIVE, 2)
    repo.save(t2)
    
    saved = repo.get_by_urn("urn1")
    assert saved.aggregate_version == 2

def test_occ_stale_update(conn):
    repo = PostgresThesisRepository(conn)
    repo.save(Thesis("urn1", "s1", LifecycleState.PROPOSED, 1))
    
    with pytest.raises(ConcurrencyDriftError):
        repo.save(Thesis("urn1", "s2", LifecycleState.ACTIVE, 1))
        
    with pytest.raises(ConcurrencyDriftError):
        repo.save(Thesis("urn1", "s2", LifecycleState.ACTIVE, 3))

def test_occ_concurrent_writer_simulation(conn):
    repo = PostgresThesisRepository(conn)
    repo.save(Thesis("urn1", "s1", LifecycleState.PROPOSED, 1))
    
    writer_a = repo.get_by_urn("urn1")
    writer_b = repo.get_by_urn("urn1")
    
    writer_a.current_status = LifecycleState.ACTIVE
    writer_a.aggregate_version = 2
    repo.save(writer_a)
    
    writer_b.current_status = LifecycleState.REFINING
    writer_b.aggregate_version = 2
    with pytest.raises(ConcurrencyDriftError):
        repo.save(writer_b)

def test_cqrs_active_lookup(conn):
    repo = PostgresThesisRepository(conn)
    repo.save(Thesis("urn1", "s1", LifecycleState.PROPOSED, 1))
    repo.save(Thesis("urn2", "s2", LifecycleState.ACTIVE, 1))
    repo.save(Thesis("urn3", "s3", LifecycleState.INVALIDATED, 1))
    
    active = repo.list_active(limit=10)
    assert len(active) == 1
    assert active[0].thesis_urn == "urn2"
    assert active[0].current_status == LifecycleState.ACTIVE

def test_pagination(conn):
    repo = PostgresThesisRepository(conn)
    repo.save(Thesis("urn1", "s", LifecycleState.ACTIVE, 1))
    repo.save(Thesis("urn3", "s", LifecycleState.ACTIVE, 1))
    repo.save(Thesis("urn2", "s", LifecycleState.ACTIVE, 1))
    
    page1 = repo.list_active(limit=2)
    assert len(page1) == 2
    assert [x.thesis_urn for x in page1] == ["urn1", "urn2"]
    
    page2 = repo.list_active(limit=2, last_urn="urn2")
    assert len(page2) == 1
    assert page2[0].thesis_urn == "urn3"

def test_lineage_snapshot(conn):
    repo = PostgresThesisSnapshotRepository(conn)
    repo.save(ThesisSnapshot("A", 1, LifecycleState.ACTIVE, "reg", None, None, []))
    repo.save(ThesisSnapshot("B", 2, LifecycleState.ACTIVE, "reg", "A", None, []))
    repo.save(ThesisSnapshot("C", 3, LifecycleState.ACTIVE, "reg", "B", None, []))
    
    lin = repo.fetch_snapshot_lineage("C")
    assert [x.snapshot_urn for x in lin] == ["C", "B", "A"]
    
def test_lineage_transition(conn):
    repo = PostgresThesisTransitionRepository(conn)
    d = ThesisDelta("d", "h", [], [])
    repo.save(ThesisTransition("A", None, None, d))
    repo.save(ThesisTransition("B", "A", None, d))
    repo.save(ThesisTransition("C", "B", None, d))
    
    lin = repo.fetch_transition_lineage("C")
    assert [x.transition_urn for x in lin] == ["C", "B", "A"]

def test_lineage_cycle_snapshot(conn):
    repo = PostgresThesisSnapshotRepository(conn)
    c = repo.conn.cursor()
    c.execute("INSERT INTO thesis_snapshots (snapshot_urn, snapshot_version, lifecycle_state, origin_regime_snapshot_urn, supersedes_snapshot_urn, invalidates_snapshot_urn) VALUES ('A', 1, 'ACTIVE', 'r', 'B', NULL)")
    c.execute("INSERT INTO thesis_snapshots (snapshot_urn, snapshot_version, lifecycle_state, origin_regime_snapshot_urn, supersedes_snapshot_urn, invalidates_snapshot_urn) VALUES ('B', 1, 'ACTIVE', 'r', 'A', NULL)")
    
    with pytest.raises(LineageCycleError):
        repo.fetch_snapshot_lineage("A")

def test_lineage_cycle_transition(conn):
    repo = PostgresThesisTransitionRepository(conn)
    c = repo.conn.cursor()
    c.execute("INSERT INTO thesis_transitions (transition_urn, supersedes_transition_urn, invalidates_transition_urn, delta_urn, delta_manifest_hash, added_assumptions, removed_assumptions) VALUES ('A', 'B', NULL, 'd', 'h', '[]', '[]')")
    c.execute("INSERT INTO thesis_transitions (transition_urn, supersedes_transition_urn, invalidates_transition_urn, delta_urn, delta_manifest_hash, added_assumptions, removed_assumptions) VALUES ('B', 'A', NULL, 'd', 'h', '[]', '[]')")
    
    with pytest.raises(LineageCycleError):
        repo.fetch_transition_lineage("A")

def test_immutability_snapshot(conn):
    s_repo = PostgresThesisSnapshotRepository(conn)
    s = ThesisSnapshot("A", 1, LifecycleState.ACTIVE, "reg", None, None, [])
    s_repo.save(s)
    with pytest.raises(ImmutableMutationError):
        s_repo.save(s)

def test_immutability_transition_and_delta(conn):
    t_repo = PostgresThesisTransitionRepository(conn)
    t = ThesisTransition("A", None, None, ThesisDelta("d", "h", [], []))
    t_repo.save(t)
    with pytest.raises(ImmutableMutationError):
        t_repo.save(t)
        
    v_repo = PostgresAssumptionVersionRepository(conn)
    v = ThesisAssumptionVersion("A", 1, "s", 0.5, AssumptionLifecycleState.ACTIVE, "h", None)
    v_repo.save(v)
    with pytest.raises(ImmutableMutationError):
        v_repo.save(v)
        
def test_missing_coverage_postgres(conn):
    repo = PostgresThesisRepository(conn)
    repo.save(Thesis("concurrent_urn", "s", LifecycleState.ACTIVE, 1))
    c = conn.cursor()
    c.execute("DELETE FROM theses WHERE thesis_urn = 'concurrent_urn'")
    with pytest.raises(ConcurrencyDriftError):
        repo.save(Thesis("concurrent_urn", "s2", LifecycleState.ACTIVE, 2))
        
    t_repo = PostgresThesisTransitionRepository(conn)
    t = ThesisTransition("T_json", None, None, ThesisDelta("d", "h", ["a"], ["b"]))
    t_repo.save(t)
    loaded = t_repo.get_by_urn("T_json")
    assert loaded.delta.added_assumptions == ["a"]
    
    v_repo = PostgresAssumptionVersionRepository(conn)
    from karsa.thesis.domain.value_objects import CalibrationReference
    cal = CalibrationReference("c1", "h1")
    v = ThesisAssumptionVersion("A_json", 1, "s", 0.5, AssumptionLifecycleState.ACTIVE, "h", cal)
    v_repo.save(v)
    loaded_v = v_repo.get_by_urn_and_version("A_json", 1)
    assert loaded_v.calibrated_confidence_reference.calibration_urn == "c1"

def test_missing_lines_and_explain(conn):
    repo = PostgresThesisRepository(conn)
    assert repo.get_by_urn("missing") is None
    
    s_repo = PostgresThesisSnapshotRepository(conn)
    assert s_repo.get_by_urn("missing") is None
    
    t_repo = PostgresThesisTransitionRepository(conn)
    assert t_repo.get_by_urn("missing") is None
    
    i_repo = PostgresAssumptionIdentityRepository(conn)
    i_repo.save(ThesisAssumptionIdentity("I"))
    assert i_repo.get_by_urn("I").assumption_urn == "I"
    assert i_repo.get_by_urn("missing") is None
    
    v_repo = PostgresAssumptionVersionRepository(conn)
    assert v_repo.get_by_urn_and_version("missing", 1) is None
    
    s_repo.save(ThesisSnapshot("E", 1, LifecycleState.ACTIVE, "reg", None, None, []))
    assert s_repo.get_by_urn("E") is not None

def test_explain_analyze(conn):
    repo = PostgresThesisRepository(conn)
    repo.save(Thesis("urn1", "s1", LifecycleState.ACTIVE, 1))
    c = conn.cursor()
    c.execute("EXPLAIN ANALYZE SELECT thesis_urn FROM theses WHERE current_status = 'ACTIVE' ORDER BY thesis_urn LIMIT 10")
    plan = c.fetchall()
    
    # Log plan to stdout for capture
    print("EXPLAIN ANALYZE OUTPUT:")
    for row in plan:
        print(row[0])
    
    # Assert index is used
    plan_str = " ".join([r[0] for r in plan])
    assert "Index Scan" in plan_str or "Index Only Scan" in plan_str or "Bitmap Index Scan" in plan_str
