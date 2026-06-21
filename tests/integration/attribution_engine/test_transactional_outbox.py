"""Transactional outbox tests — Sprint-09 F-02."""
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
    conn.autocommit = False
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def cleanup(conn):
    yield
    conn.rollback()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE attribution_records DISABLE TRIGGER ALL")
        cur.execute("DELETE FROM attribution_records WHERE attribution_id LIKE 'txn-%'")
        cur.execute("ALTER TABLE attribution_records ENABLE TRIGGER ALL")
        cur.execute("DELETE FROM attribution_version_registry WHERE attribution_id LIKE 'txn-%'")
        cur.execute("DELETE FROM attribution_outbox WHERE outbox_id LIKE 'txn-%'")
    conn.autocommit = False


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


def _insert_registry(conn, evaluation_id, algorithm_version, attribution_id):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO attribution_version_registry (
                evaluation_id, algorithm_version, attribution_id, attribution_status
            ) VALUES (%s, %s, %s, 'CANONICAL')""",
            (evaluation_id, algorithm_version, attribution_id)
        )


def _insert_outbox(conn, outbox_id, aggregate_id):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO attribution_outbox (
                outbox_id, event_type, payload, aggregate_id, status
            ) VALUES (%s, 'TestEvent', '{}', %s, 'PENDING')""",
            (outbox_id, aggregate_id)
        )


def _count_records(conn, table, column, value):
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} = %s", (value,))
        return cur.fetchone()[0]


class TestTransactionalOutbox:
    def test_all_three_inserts_commit(self, conn):
        """When all inserts succeed, all records persist."""
        eval_id = f"test-eval-{uuid.uuid4().hex[:8]}"
        attr_id = f"txn-attr-{uuid.uuid4().hex[:8]}"
        outbox_id = f"txn-out-{uuid.uuid4().hex[:8]}"

        _insert_attribution(conn, attr_id, eval_id, "v1.0")
        _insert_registry(conn, eval_id, "v1.0", attr_id)
        _insert_outbox(conn, outbox_id, attr_id)
        conn.commit()

        assert _count_records(conn, "attribution_records", "attribution_id", attr_id) == 1
        assert _count_records(conn, "attribution_version_registry", "attribution_id", attr_id) == 1
        assert _count_records(conn, "attribution_outbox", "outbox_id", outbox_id) == 1

    def test_rollback_when_record_insert_fails(self, conn):
        """When record insert fails, nothing persists."""
        eval_id = f"test-eval-{uuid.uuid4().hex[:8]}"
        attr_id = f"txn-attr-{uuid.uuid4().hex[:8]}"
        outbox_id = f"txn-out-{uuid.uuid4().hex[:8]}"

        # First insert succeeds
        _insert_attribution(conn, attr_id, eval_id, "v1.0")

        # Second insert with same PK fails
        with pytest.raises(psycopg.errors.UniqueViolation):
            _insert_attribution(conn, attr_id, eval_id, "v1.0")

        conn.rollback()

        assert _count_records(conn, "attribution_records", "attribution_id", attr_id) == 0

    def test_rollback_when_registry_insert_fails(self, conn):
        """When registry insert fails, record and outbox also roll back."""
        eval_id = f"test-eval-{uuid.uuid4().hex[:8]}"
        attr_id = f"txn-attr-{uuid.uuid4().hex[:8]}"
        outbox_id = f"txn-out-{uuid.uuid4().hex[:8]}"

        _insert_attribution(conn, attr_id, eval_id, "v1.0")

        # Duplicate canonical fails
        attr_id_2 = f"txn-attr-{uuid.uuid4().hex[:8]}"
        _insert_attribution(conn, attr_id_2, eval_id, "v2.0")
        _insert_registry(conn, eval_id, "v1.0", attr_id)

        with pytest.raises(psycopg.errors.UniqueViolation):
            _insert_registry(conn, eval_id, "v2.0", attr_id_2)

        conn.rollback()

        assert _count_records(conn, "attribution_records", "evaluation_id", eval_id) == 0
        assert _count_records(conn, "attribution_version_registry", "evaluation_id", eval_id) == 0

    def test_rollback_when_outbox_insert_fails(self, conn):
        """When outbox insert fails, record and registry also roll back."""
        eval_id = f"test-eval-{uuid.uuid4().hex[:8]}"
        attr_id = f"txn-attr-{uuid.uuid4().hex[:8]}"

        _insert_attribution(conn, attr_id, eval_id, "v1.0")
        _insert_registry(conn, eval_id, "v1.0", attr_id)

        # Outbox with NULL outbox_id fails NOT NULL constraint
        with pytest.raises(psycopg.errors.NotNullViolation):
            _insert_outbox(conn, None, attr_id)

        conn.rollback()

        assert _count_records(conn, "attribution_records", "attribution_id", attr_id) == 0
        assert _count_records(conn, "attribution_version_registry", "attribution_id", attr_id) == 0
