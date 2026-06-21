"""Canonical supersede workflow tests — Sprint-09 F-09."""
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
        cur.execute("ALTER TABLE attribution_records DISABLE TRIGGER ALL")
        cur.execute("DELETE FROM attribution_records WHERE evaluation_id LIKE 'sup-%'")
        cur.execute("ALTER TABLE attribution_records ENABLE TRIGGER ALL")
        cur.execute("DELETE FROM attribution_version_registry WHERE evaluation_id LIKE 'sup-%'")


def _insert_attribution(conn, attribution_id, evaluation_id, algorithm_version):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO attribution_records (
                attribution_id, evaluation_id, algorithm_version,
                decision_id, evaluation_horizon_days, target_urn, target_type,
                total_realized_return_bps, total_expected_return_bps, total_variance_bps,
                contributions, attribution_summary, attribution_quality,
                quality_provenance, context_snapshot,
                source_request_id, attributed_at, attributed_by
            ) VALUES (%s, %s, %s, 'dec-1', 30, 'worker-1', 'DECISION',
                100, 50, 50, '[]', '{}', '{}', '{}', '{}', 'req-1', NOW(), 'test')""",
            (attribution_id, evaluation_id, algorithm_version)
        )


def _insert_registry(conn, evaluation_id, algorithm_version, attribution_id, status='CANONICAL'):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO attribution_version_registry (
                evaluation_id, algorithm_version, attribution_id, attribution_status
            ) VALUES (%s, %s, %s, %s)""",
            (evaluation_id, algorithm_version, attribution_id, status)
        )


def _supersede_previous(conn, evaluation_id, new_attribution_id):
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE attribution_version_registry
            SET attribution_status = 'SUPERSEDED', superseded_by = %s, updated_at = NOW()
            WHERE evaluation_id = %s AND attribution_status = 'CANONICAL'""",
            (new_attribution_id, evaluation_id)
        )


class TestSupersedePreviousCanonical:
    def test_supersede_previous_canonical(self, conn):
        eval_id = f"sup-eval-{uuid.uuid4().hex[:8]}"
        attr_id_1 = f"sup-attr-{uuid.uuid4().hex[:8]}"
        attr_id_2 = f"sup-attr-{uuid.uuid4().hex[:8]}"

        # Setup: v1 is canonical
        _insert_attribution(conn, attr_id_1, eval_id, "v1.0")
        _insert_registry(conn, eval_id, "v1.0", attr_id_1, "CANONICAL")

        # Setup: v2 attribution exists
        _insert_attribution(conn, attr_id_2, eval_id, "v2.0")

        # Act: supersede v1
        _supersede_previous(conn, eval_id, attr_id_2)
        _insert_registry(conn, eval_id, "v2.0", attr_id_2, "CANONICAL")

        # Assert: v1 is superseded
        with conn.cursor() as cur:
            cur.execute("SELECT attribution_status, superseded_by FROM attribution_version_registry WHERE evaluation_id = %s AND algorithm_version = 'v1.0'", (eval_id,))
            row = cur.fetchone()
            assert row[0] == "SUPERSEDED"
            assert row[1] == attr_id_2

    def test_single_canonical_after_transition(self, conn):
        eval_id = f"sup-eval-{uuid.uuid4().hex[:8]}"
        attr_id_1 = f"sup-attr-{uuid.uuid4().hex[:8]}"
        attr_id_2 = f"sup-attr-{uuid.uuid4().hex[:8]}"

        _insert_attribution(conn, attr_id_1, eval_id, "v1.0")
        _insert_registry(conn, eval_id, "v1.0", attr_id_1, "CANONICAL")
        _insert_attribution(conn, attr_id_2, eval_id, "v2.0")
        _supersede_previous(conn, eval_id, attr_id_2)
        _insert_registry(conn, eval_id, "v2.0", attr_id_2, "CANONICAL")

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM attribution_version_registry WHERE evaluation_id = %s AND attribution_status = 'CANONICAL'", (eval_id,))
            assert cur.fetchone()[0] == 1

    def test_registry_reflects_supersede_transition(self, conn):
        eval_id = f"sup-eval-{uuid.uuid4().hex[:8]}"
        attr_id_1 = f"sup-attr-{uuid.uuid4().hex[:8]}"
        attr_id_2 = f"sup-attr-{uuid.uuid4().hex[:8]}"

        _insert_attribution(conn, attr_id_1, eval_id, "v1.0")
        _insert_registry(conn, eval_id, "v1.0", attr_id_1, "CANONICAL")
        _insert_attribution(conn, attr_id_2, eval_id, "v2.0")
        _supersede_previous(conn, eval_id, attr_id_2)
        _insert_registry(conn, eval_id, "v2.0", attr_id_2, "CANONICAL")

        with conn.cursor() as cur:
            cur.execute("SELECT algorithm_version, attribution_status FROM attribution_version_registry WHERE evaluation_id = %s ORDER BY algorithm_version", (eval_id,))
            rows = cur.fetchall()
            assert rows[0] == ("v1.0", "SUPERSEDED")
            assert rows[1] == ("v2.0", "CANONICAL")

    def test_projection_uses_new_canonical(self, conn):
        eval_id = f"sup-eval-{uuid.uuid4().hex[:8]}"
        attr_id_1 = f"sup-attr-{uuid.uuid4().hex[:8]}"
        attr_id_2 = f"sup-attr-{uuid.uuid4().hex[:8]}"

        # v1 has contribution_bps=30
        _insert_attribution(conn, attr_id_1, eval_id, "v1.0")
        _insert_registry(conn, eval_id, "v1.0", attr_id_1, "CANONICAL")

        # v2 has different contribution (simulate)
        _insert_attribution(conn, attr_id_2, eval_id, "v2.0")
        _supersede_previous(conn, eval_id, attr_id_2)
        _insert_registry(conn, eval_id, "v2.0", attr_id_2, "CANONICAL")

        # Rebuild projection using canonical only
        with conn.cursor() as cur:
            cur.execute("""
                SELECT v.algorithm_version
                FROM attribution_records a
                JOIN attribution_version_registry v ON v.attribution_id = a.attribution_id
                WHERE a.evaluation_id = %s AND v.attribution_status = 'CANONICAL'
            """, (eval_id,))
            row = cur.fetchone()
            assert row[0] == "v2.0"

    def test_old_canonical_excluded_from_projection(self, conn):
        eval_id = f"sup-eval-{uuid.uuid4().hex[:8]}"
        attr_id_1 = f"sup-attr-{uuid.uuid4().hex[:8]}"
        attr_id_2 = f"sup-attr-{uuid.uuid4().hex[:8]}"

        _insert_attribution(conn, attr_id_1, eval_id, "v1.0")
        _insert_registry(conn, eval_id, "v1.0", attr_id_1, "CANONICAL")
        _insert_attribution(conn, attr_id_2, eval_id, "v2.0")
        _supersede_previous(conn, eval_id, attr_id_2)
        _insert_registry(conn, eval_id, "v2.0", attr_id_2, "CANONICAL")

        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM attribution_records a
                JOIN attribution_version_registry v ON v.attribution_id = a.attribution_id
                WHERE a.evaluation_id = %s AND v.attribution_status = 'SUPERSEDED'
            """, (eval_id,))
            assert cur.fetchone()[0] == 1
