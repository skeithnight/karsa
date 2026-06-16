import pytest
import psycopg2
from karsa.thesis.domain.models import Thesis, ThesisSnapshot
from karsa.thesis.domain.value_objects import LifecycleState
from karsa.thesis.infrastructure.storage.postgres.postgres_repo import PostgresThesisRepository, PostgresThesisSnapshotRepository

@pytest.fixture
def conn():
    import os
    db_name = os.environ.get("POSTGRES_DB", "postgres")
    db_user = os.environ.get("POSTGRES_USER", "postgres")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "postgres")
    db_host = os.environ.get("POSTGRES_HOST", "localhost")
    db_port = int(os.environ.get("POSTGRES_PORT", 5433))
    connection = psycopg2.connect(dbname=db_name, user=db_user, password=db_pass, host=db_host, port=db_port)
    # We deliberately DO NOT set autocommit = True
    # so we can test transactions and rollbacks
    yield connection
    connection.rollback()
    connection.close()

def setup_db(conn):
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS theses CASCADE")
    c.execute("DROP TABLE IF EXISTS thesis_snapshots CASCADE")
    c.execute("CREATE TABLE theses (thesis_urn TEXT PRIMARY KEY, current_snapshot_urn TEXT, current_status TEXT, aggregate_version INT)")
    c.execute("CREATE TABLE thesis_snapshots (snapshot_urn TEXT PRIMARY KEY, snapshot_version INT, lifecycle_state TEXT, origin_regime_snapshot_urn TEXT, supersedes_snapshot_urn TEXT, invalidates_snapshot_urn TEXT)")
    conn.commit()

def test_cqrs_scenario_a_snapshot_succeeds_root_fails(conn):
    setup_db(conn)
    r_t = PostgresThesisRepository(conn)
    r_s = PostgresThesisSnapshotRepository(conn)
    
    t = Thesis("T1", "S1", LifecycleState.PROPOSED, 1)
    s = ThesisSnapshot("S1", 1, LifecycleState.ACTIVE, "R", None, None, [])
    
    try:
        r_s.save(s) # Snapshot succeeds
        # Force a failure in root
        c = conn.cursor()
        c.execute("DROP TABLE theses CASCADE") # Force DB error
        r_t.save(t) # Fails
        conn.commit()
    except Exception:
        conn.rollback()
    
    # Prove they didn't diverge because the whole transaction rolled back
    setup_db(conn) # Just to be able to query without missing tables
    assert r_s.get_by_urn("S1") is None
    assert r_t.get_by_urn("T1") is None

def test_cqrs_scenario_b_root_succeeds_snapshot_fails(conn):
    setup_db(conn)
    r_t = PostgresThesisRepository(conn)
    r_s = PostgresThesisSnapshotRepository(conn)
    
    t = Thesis("T2", "S2", LifecycleState.PROPOSED, 1)
    s = ThesisSnapshot("S2", 1, LifecycleState.ACTIVE, "R", None, None, [])
    
    try:
        r_t.save(t) # Root succeeds
        c = conn.cursor()
        c.execute("DROP TABLE thesis_snapshots CASCADE") # Force DB error
        r_s.save(s) # Snapshot fails
        conn.commit()
    except Exception:
        conn.rollback()
        
    setup_db(conn)
    assert r_s.get_by_urn("S2") is None
    assert r_t.get_by_urn("T2") is None

def test_cqrs_scenario_c_transaction_rollback(conn):
    setup_db(conn)
    r_t = PostgresThesisRepository(conn)
    r_s = PostgresThesisSnapshotRepository(conn)
    
    t = Thesis("T3", "S3", LifecycleState.PROPOSED, 1)
    s = ThesisSnapshot("S3", 1, LifecycleState.ACTIVE, "R", None, None, [])
    
    r_t.save(t)
    r_s.save(s)
    conn.rollback() # Explicit rollback
    
    assert r_s.get_by_urn("S3") is None
    assert r_t.get_by_urn("T3") is None

