"""Migration integration tests — Sprint-10 Wave-2."""
import pytest
import uuid
import json
from datetime import datetime
import psycopg


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
        # Clean up test data
        cur.execute("ALTER TABLE review_assessments DISABLE TRIGGER ALL")
        cur.execute("DELETE FROM review_assessments WHERE review_id LIKE 'mig-%'")
        cur.execute("ALTER TABLE review_assessments ENABLE TRIGGER ALL")
        cur.execute("DELETE FROM review_version_registry WHERE review_id LIKE 'mig-%'")
        cur.execute("DELETE FROM review_outbox WHERE outbox_id LIKE 'mig-%'")


def _insert_assessment(conn, review_id, evaluation_id="eval-1", review_type="WORKER", review_version="v1.0"):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO review_assessments (
                review_id, evaluation_id, review_type, review_version,
                target_urn, target_type, decision_id, attribution_id,
                findings, recommendations, review_summary, review_quality,
                context_snapshot, reviewed_at, reviewed_by
            ) VALUES (%s, %s, %s, %s, 'worker-1', 'WORKER', 'dec-1', 'attr-1',
                '[]', '{}', '{}', '{}', '{}', NOW(), 'test')""",
            (review_id, evaluation_id, review_type, review_version)
        )


def _insert_registry(conn, evaluation_id, review_type, review_version, review_id, status='CANONICAL'):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO review_version_registry (
                evaluation_id, review_type, review_version, review_id, review_status
            ) VALUES (%s, %s, %s, %s, %s)""",
            (evaluation_id, review_type, review_version, review_id, status)
        )


# --- Migration Apply Tests ---

class TestMigrationApply:
    def test_review_assessments_exists(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'review_assessments'")
            assert cur.fetchone()[0] == 1

    def test_review_version_registry_exists(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'review_version_registry'")
            assert cur.fetchone()[0] == 1

    def test_worker_review_projection_exists(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'worker_review_projection'")
            assert cur.fetchone()[0] == 1

    def test_thesis_review_projection_exists(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'thesis_review_projection'")
            assert cur.fetchone()[0] == 1

    def test_capability_gap_projection_exists(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'capability_gap_projection'")
            assert cur.fetchone()[0] == 1

    def test_review_coverage_projection_exists(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'review_coverage_projection'")
            assert cur.fetchone()[0] == 1

    def test_review_outbox_exists(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'review_outbox'")
            assert cur.fetchone()[0] == 1


# --- Immutability Trigger Tests ---

class TestImmutabilityTrigger:
    def test_update_blocked(self, conn):
        _insert_assessment(conn, "mig-imm-1")
        with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
            with conn.cursor() as cur:
                cur.execute("UPDATE review_assessments SET reviewed_by = 'hacked' WHERE review_id = 'mig-imm-1'")

    def test_delete_blocked(self, conn):
        _insert_assessment(conn, "mig-imm-2")
        with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
            with conn.cursor() as cur:
                cur.execute("DELETE FROM review_assessments WHERE review_id = 'mig-imm-2'")


# --- Canonical Index Tests ---

class TestCanonicalIndex:
    def test_first_canonical_succeeds(self, conn):
        _insert_assessment(conn, "mig-can-1", "eval-can-1", "WORKER", "v1.0")
        _insert_registry(conn, "eval-can-1", "WORKER", "v1.0", "mig-can-1", "CANONICAL")
        with conn.cursor() as cur:
            cur.execute("SELECT review_status FROM review_version_registry WHERE review_id = 'mig-can-1'")
            assert cur.fetchone()[0] == "CANONICAL"

    def test_second_canonical_fails(self, conn):
        _insert_assessment(conn, "mig-can-2a", "eval-can-2", "WORKER", "v1.0")
        _insert_registry(conn, "eval-can-2", "WORKER", "v1.0", "mig-can-2a", "CANONICAL")
        _insert_assessment(conn, "mig-can-2b", "eval-can-2", "WORKER", "v2.0")
        with pytest.raises(psycopg.errors.UniqueViolation):
            _insert_registry(conn, "eval-can-2", "WORKER", "v2.0", "mig-can-2b", "CANONICAL")

    def test_supersede_then_new_canonical(self, conn):
        _insert_assessment(conn, "mig-can-3a", "eval-can-3", "WORKER", "v1.0")
        _insert_registry(conn, "eval-can-3", "WORKER", "v1.0", "mig-can-3a", "CANONICAL")
        _insert_assessment(conn, "mig-can-3b", "eval-can-3", "WORKER", "v2.0")
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE review_version_registry SET review_status = 'SUPERSEDED' WHERE evaluation_id = 'eval-can-3' AND review_status = 'CANONICAL'"
            )
        _insert_registry(conn, "eval-can-3", "WORKER", "v2.0", "mig-can-3b", "CANONICAL")
        with conn.cursor() as cur:
            cur.execute("SELECT review_status FROM review_version_registry WHERE review_id = 'mig-can-3a'")
            assert cur.fetchone()[0] == "SUPERSEDED"
            cur.execute("SELECT review_status FROM review_version_registry WHERE review_id = 'mig-can-3b'")
            assert cur.fetchone()[0] == "CANONICAL"

    def test_multiple_review_types_allowed(self, conn):
        _insert_assessment(conn, "mig-can-4w", "eval-can-4", "WORKER", "v1.0")
        _insert_registry(conn, "eval-can-4", "WORKER", "v1.0", "mig-can-4w", "CANONICAL")
        _insert_assessment(conn, "mig-can-4t", "eval-can-4", "THESIS", "v1.0")
        _insert_registry(conn, "eval-can-4", "THESIS", "v1.0", "mig-can-4t", "CANONICAL")
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM review_version_registry WHERE evaluation_id = 'eval-can-4' AND review_status = 'CANONICAL'")
            assert cur.fetchone()[0] == 2


# --- Foreign Key Tests ---

class TestForeignKey:
    def test_registry_fk_to_assessment(self, conn):
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            _insert_registry(conn, "eval-fk-1", "WORKER", "v1.0", "nonexistent", "CANONICAL")


# --- Status Check Constraint Tests ---

class TestStatusConstraint:
    def test_valid_statuses(self, conn):
        for status in ("CANONICAL", "SUPERSEDED", "EXPERIMENTAL"):
            _insert_assessment(conn, f"mig-status-{status}", f"eval-{status}", "WORKER", "v1.0")
            _insert_registry(conn, f"eval-{status}", "WORKER", "v1.0", f"mig-status-{status}", status)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM review_version_registry WHERE review_id LIKE 'mig-status-%'")
            assert cur.fetchone()[0] == 3

    def test_invalid_status_raises(self, conn):
        _insert_assessment(conn, "mig-status-bad", "eval-bad", "WORKER", "v1.0")
        with pytest.raises(psycopg.errors.CheckViolation):
            _insert_registry(conn, "eval-bad", "WORKER", "v1.0", "mig-status-bad", "INVALID")


# --- Outbox Tests ---

class TestOutbox:
    def test_outbox_insert(self, conn):
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO review_outbox (outbox_id, event_type, payload, aggregate_id)
                VALUES ('mig-out-1', 'TestEvent', '{}', 'agg-1')"""
            )
            cur.execute("SELECT status FROM review_outbox WHERE outbox_id = 'mig-out-1'")
            assert cur.fetchone()[0] == "PENDING"

    def test_outbox_status_update(self, conn):
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO review_outbox (outbox_id, event_type, payload, aggregate_id)
                VALUES ('mig-out-2', 'TestEvent', '{}', 'agg-2')"""
            )
            cur.execute("UPDATE review_outbox SET status = 'SENT', sent_at = NOW() WHERE outbox_id = 'mig-out-2'")
            cur.execute("SELECT status FROM review_outbox WHERE outbox_id = 'mig-out-2'")
            assert cur.fetchone()[0] == "SENT"

    def test_invalid_outbox_status_raises(self, conn):
        with pytest.raises(psycopg.errors.CheckViolation):
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO review_outbox (outbox_id, event_type, payload, aggregate_id, status)
                    VALUES ('mig-out-3', 'TestEvent', '{}', 'agg-3', 'INVALID')"""
                )
