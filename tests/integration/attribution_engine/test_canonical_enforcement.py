"""Canonical enforcement tests — Sprint-09 F-01."""
import pytest
import uuid
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
        cur.execute("ALTER TABLE attribution_version_registry DISABLE TRIGGER ALL")
        cur.execute("DELETE FROM attribution_version_registry WHERE evaluation_id LIKE 'test-%'")
        cur.execute("ALTER TABLE attribution_records DISABLE TRIGGER ALL")
        cur.execute("DELETE FROM attribution_records WHERE evaluation_id LIKE 'test-%'")
        cur.execute("ALTER TABLE attribution_records ENABLE TRIGGER ALL")
        cur.execute("ALTER TABLE attribution_version_registry ENABLE TRIGGER ALL")


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


class TestFirstCanonicalSucceeds:
    def test_first_canonical_succeeds(self, conn):
        eval_id = f"test-eval-{uuid.uuid4().hex[:8]}"
        attr_id = f"test-attr-{uuid.uuid4().hex[:8]}"

        _insert_attribution(conn, attr_id, eval_id, "v1.0")
        _insert_registry(conn, eval_id, "v1.0", attr_id, "CANONICAL")

        with conn.cursor() as cur:
            cur.execute(
                "SELECT attribution_status FROM attribution_version_registry WHERE evaluation_id = %s",
                (eval_id,)
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == "CANONICAL"


class TestSecondCanonicalFails:
    def test_second_canonical_fails(self, conn):
        eval_id = f"test-eval-{uuid.uuid4().hex[:8]}"
        attr_id_1 = f"test-attr-{uuid.uuid4().hex[:8]}"
        attr_id_2 = f"test-attr-{uuid.uuid4().hex[:8]}"

        _insert_attribution(conn, attr_id_1, eval_id, "v1.0")
        _insert_registry(conn, eval_id, "v1.0", attr_id_1, "CANONICAL")

        _insert_attribution(conn, attr_id_2, eval_id, "v2.0")

        with pytest.raises(psycopg.errors.UniqueViolation):
            _insert_registry(conn, eval_id, "v2.0", attr_id_2, "CANONICAL")


class TestSupersedePreviousCanonical:
    def test_supersede_workflow(self, conn):
        eval_id = f"test-eval-{uuid.uuid4().hex[:8]}"
        attr_id_1 = f"test-attr-{uuid.uuid4().hex[:8]}"
        attr_id_2 = f"test-attr-{uuid.uuid4().hex[:8]}"

        _insert_attribution(conn, attr_id_1, eval_id, "v1.0")
        _insert_registry(conn, eval_id, "v1.0", attr_id_1, "CANONICAL")

        _insert_attribution(conn, attr_id_2, eval_id, "v2.0")

        # Supersede previous
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE attribution_version_registry
                SET attribution_status = 'SUPERSEDED', superseded_by = %s, updated_at = NOW()
                WHERE evaluation_id = %s AND attribution_status = 'CANONICAL'""",
                (attr_id_2, eval_id)
            )

        # Now new canonical can be inserted
        _insert_registry(conn, eval_id, "v2.0", attr_id_2, "CANONICAL")

        with conn.cursor() as cur:
            cur.execute(
                "SELECT attribution_status, superseded_by FROM attribution_version_registry WHERE evaluation_id = %s AND algorithm_version = 'v1.0'",
                (eval_id,)
            )
            row = cur.fetchone()
            assert row[0] == "SUPERSEDED"
            assert row[1] == attr_id_2

            cur.execute(
                "SELECT attribution_status FROM attribution_version_registry WHERE evaluation_id = %s AND algorithm_version = 'v2.0'",
                (eval_id,)
            )
            row = cur.fetchone()
            assert row[0] == "CANONICAL"
