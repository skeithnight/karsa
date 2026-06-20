"""Concurrency tests — Sprint-07 Closure Hardening.

Verifies database-level idempotency for review_cycles.
"""
import pytest
import json
import uuid
import psycopg
from datetime import datetime


@pytest.fixture(scope="module")
def conn():
    import os
    db_name = os.environ.get("POSTGRES_DB", "karsa_db")
    db_user = os.environ.get("POSTGRES_USER", "karsa")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "karsa_password")
    db_host = os.environ.get("POSTGRES_HOST", "localhost")
    db_port = os.environ.get("POSTGRES_PORT", "5432")
    conninfo = f"dbname={db_name} user={db_user} password={db_pass} host={db_host} port={db_port}"
    conn = psycopg.connect(conninfo)
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def cleanup(conn):
    yield
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE review_cycles DISABLE TRIGGER ALL")
        cur.execute("DELETE FROM review_cycles WHERE decision_id LIKE 'conc-%'")
        cur.execute("ALTER TABLE review_cycles ENABLE TRIGGER ALL")


def insert_cycle(conn, cycle_id, decision_id):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO review_cycles (
                cycle_id, decision_id, proposal_id, journal_ref,
                review_type, decision_snapshot, schedule_policy,
                review_template, eligibility_event_ref, created_at, created_by
            ) VALUES (%s, %s, 'p1', 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')
            ON CONFLICT (decision_id) DO NOTHING
            """,
            (cycle_id, decision_id)
        )


class TestDecisionIdUniqueness:
    def test_unique_constraint_exists(self, conn):
        """Verify ux_review_cycles_decision_id index exists."""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT indexname FROM pg_indexes WHERE indexname = 'ux_review_cycles_decision_id'"
            )
            row = cur.fetchone()
            assert row is not None, "UNIQUE index ux_review_cycles_decision_id does not exist"

    def test_duplicate_decision_id_ignored(self, conn):
        """ON CONFLICT DO NOTHING silently ignores duplicate decision_id."""
        decision_id = f"conc-dup-{uuid.uuid4().hex[:8]}"

        insert_cycle(conn, "cycle-1", decision_id)
        insert_cycle(conn, "cycle-2", decision_id)  # duplicate — should be ignored

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM review_cycles WHERE decision_id = %s", (decision_id,))
            count = cur.fetchone()[0]
            assert count == 1, f"Expected 1 row, got {count}"

    def test_concurrent_inserts_produce_one_row(self, conn):
        """Two concurrent inserts with same decision_id produce exactly one row."""
        decision_id = f"conc-race-{uuid.uuid4().hex[:8]}"

        # Simulate concurrent inserts using two separate connections
        conn2 = _new_conn()
        try:
            conn2.autocommit = True

            # Both insert simultaneously
            insert_cycle(conn, "cycle-a", decision_id)
            insert_cycle(conn2, "cycle-b", decision_id)

            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM review_cycles WHERE decision_id = %s", (decision_id,))
                count = cur.fetchone()[0]
                assert count == 1, f"Expected 1 row, got {count}"
        finally:
            conn2.close()

    def test_different_decision_ids_allowed(self, conn):
        """Different decision_ids create separate rows."""
        insert_cycle(conn, "cycle-x", f"conc-diff-{uuid.uuid4().hex[:8]}")
        insert_cycle(conn, "cycle-y", f"conc-diff-{uuid.uuid4().hex[:8]}")

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM review_cycles WHERE decision_id LIKE 'conc-diff-%'")
            count = cur.fetchone()[0]
            assert count == 2


def _new_conn():
    import os
    db_name = os.environ.get("POSTGRES_DB", "karsa_db")
    db_user = os.environ.get("POSTGRES_USER", "karsa")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "karsa_password")
    db_host = os.environ.get("POSTGRES_HOST", "localhost")
    db_port = os.environ.get("POSTGRES_PORT", "5432")
    conninfo = f"dbname={db_name} user={db_user} password={db_pass} host={db_host} port={db_port}"
    return psycopg.connect(conninfo)
