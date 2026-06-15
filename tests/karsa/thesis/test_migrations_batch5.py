import psycopg2
import pytest
from unittest.mock import patch
import sys
import os

# Append the current directory so we can import the migration
sys.path.append("/Users/dwiki.nugraha/dwikicode/karsa/alembic/versions")

# The module name starts with a number, so we use importlib
import importlib
import importlib.machinery
mig = importlib.machinery.SourceFileLoader("mig", "/Users/dwiki.nugraha/dwikicode/karsa/alembic/versions/47_thesis_evolution_init.py").load_module()

@pytest.fixture(scope="module")
def conn():
    connection = psycopg2.connect(dbname="postgres", user="postgres", password="postgres", host="localhost", port=5433)
    connection.autocommit = True
    yield connection
    connection.close()

def execute_mock(conn, sql):
    c = conn.cursor()
    c.execute(sql)

@pytest.fixture(scope="module", autouse=True)
def run_migrations(conn):
    # Downgrade first just in case
    with patch('alembic.op.execute', side_effect=lambda sql: execute_mock(conn, sql)):
        mig.downgrade()
        # Test Upgrade
        mig.upgrade()
    yield
    # We leave the schema up for other tests, or we could tear it down.

def test_migration_upgrade_downgrade(conn):
    with patch('alembic.op.execute', side_effect=lambda sql: execute_mock(conn, sql)):
        mig.downgrade()
        mig.upgrade()
        # Verify tables exist
        c = conn.cursor()
        c.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        tables = [row[0] for row in c.fetchall()]
        assert "theses" in tables
        assert "thesis_snapshots" in tables
        assert "thesis_transitions" in tables

def test_constraint_pk_fk_unique_not_null(conn):
    c = conn.cursor()
    # Test NOT NULL
    with pytest.raises(psycopg2.errors.NotNullViolation):
        c.execute("INSERT INTO theses (thesis_urn, current_snapshot_urn, current_status) VALUES ('T1', NULL, 'ACTIVE')")
    
    # Test PK
    c.execute("INSERT INTO theses (thesis_urn, current_snapshot_urn, current_status, aggregate_version) VALUES ('T1', 'S1', 'ACTIVE', 1)")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        c.execute("INSERT INTO theses (thesis_urn, current_snapshot_urn, current_status, aggregate_version) VALUES ('T1', 'S2', 'ACTIVE', 2)")

    # Test FK (thesis_snapshots -> theses)
    with pytest.raises(psycopg2.errors.ForeignKeyViolation):
        c.execute("INSERT INTO thesis_snapshots (snapshot_urn, thesis_urn, snapshot_version, snapshot_state, origin_regime_snapshot_urn, thesis_manifest_hash, evidence_manifest_hash, assumption_manifest_hash) VALUES ('S_MISSING', 'MISSING_T', 1, 'ACTIVE', 'R', 'h', 'h', 'h')")

def test_trigger_snapshot_mutation_rejection(conn):
    c = conn.cursor()
    # Insert valid snapshot
    c.execute("INSERT INTO thesis_snapshots (snapshot_urn, thesis_urn, snapshot_version, snapshot_state, origin_regime_snapshot_urn, thesis_manifest_hash, evidence_manifest_hash, assumption_manifest_hash, created_at) VALUES ('S1', 'T1', 1, 'ACTIVE', 'R', 'h', 'h', 'h', '2026-06-15 10:00:00')")
    
    with pytest.raises(psycopg2.errors.RaiseException, match="ImmutableMutationError"):
        c.execute("UPDATE thesis_snapshots SET snapshot_state = 'ARCHIVED' WHERE snapshot_urn = 'S1'")

    with pytest.raises(psycopg2.errors.RaiseException, match="ImmutableMutationError"):
        c.execute("DELETE FROM thesis_snapshots WHERE snapshot_urn = 'S1'")

def test_trigger_transition_mutation_rejection(conn):
    c = conn.cursor()
    c.execute("INSERT INTO thesis_transitions (transition_urn, thesis_urn, delta_manifest_hash) VALUES ('TR1', 'T1', 'h')")
    
    with pytest.raises(psycopg2.errors.RaiseException, match="ImmutableMutationError"):
        c.execute("UPDATE thesis_transitions SET delta_manifest_hash = 'h2' WHERE transition_urn = 'TR1'")

    with pytest.raises(psycopg2.errors.RaiseException, match="ImmutableMutationError"):
        c.execute("DELETE FROM thesis_transitions WHERE transition_urn = 'TR1'")

def test_trigger_delta_mutation_rejection(conn):
    c = conn.cursor()
    c.execute("INSERT INTO thesis_deltas (delta_urn, transition_urn, delta_manifest_hash) VALUES ('D1', 'TR1', 'h')")
    
    with pytest.raises(psycopg2.errors.RaiseException, match="ImmutableMutationError"):
        c.execute("UPDATE thesis_deltas SET delta_manifest_hash = 'h2' WHERE delta_urn = 'D1'")

    with pytest.raises(psycopg2.errors.RaiseException, match="ImmutableMutationError"):
        c.execute("DELETE FROM thesis_deltas WHERE delta_urn = 'D1'")

def test_partition_creation_and_routing(conn):
    c = conn.cursor()
    c.execute("SELECT inhrelid::regclass AS child FROM pg_inherits WHERE inhparent = 'thesis_snapshots'::regclass;")
    partitions = [row[0] for row in c.fetchall()]
    assert "thesis_snapshots_y2026m06" in partitions
    
    # Route data directly via parent
    c.execute("INSERT INTO thesis_snapshots (snapshot_urn, thesis_urn, snapshot_version, snapshot_state, origin_regime_snapshot_urn, thesis_manifest_hash, evidence_manifest_hash, assumption_manifest_hash, created_at) VALUES ('S2', 'T1', 2, 'ACTIVE', 'R', 'h', 'h', 'h', '2026-06-15 12:00:00')")
    
    # Verify it landed in the correct partition
    c.execute("SELECT snapshot_urn FROM thesis_snapshots_y2026m06 WHERE snapshot_urn = 'S2'")
    assert c.fetchone() is not None

def test_manifest_hash_fields_present(conn):
    c = conn.cursor()
    c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'thesis_snapshots'")
    cols = [row[0] for row in c.fetchall()]
    assert "thesis_manifest_hash" in cols
    assert "evidence_manifest_hash" in cols
    assert "assumption_manifest_hash" in cols

    c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'thesis_transitions'")
    t_cols = [row[0] for row in c.fetchall()]
    assert "delta_manifest_hash" in t_cols
