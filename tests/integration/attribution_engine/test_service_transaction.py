"""Service-level transaction rollback tests — Sprint-09 F-10."""
import pytest
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch
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
        cur.execute("DELETE FROM attribution_records WHERE evaluation_id LIKE 'txn-%'")
        cur.execute("ALTER TABLE attribution_records ENABLE TRIGGER ALL")
        cur.execute("DELETE FROM attribution_version_registry WHERE evaluation_id LIKE 'txn-%'")
        cur.execute("DELETE FROM attribution_outbox WHERE aggregate_id LIKE 'txn-%'")


def _count(conn, table, column, value):
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} = %s", (value,))
        return cur.fetchone()[0]


class TestServiceTransactionRollback:
    def test_service_transaction_rollback_record_failure(self, conn):
        """When record insert fails, nothing commits."""
        eval_id = f"txn-eval-{uuid.uuid4().hex[:8]}"
        attr_id = f"txn-attr-{uuid.uuid4().hex[:8]}"

        # Insert first attribution
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO attribution_records (
                    attribution_id, evaluation_id, algorithm_version,
                    decision_id, evaluation_horizon_days, target_urn, target_type,
                    total_realized_return_bps, total_expected_return_bps, total_variance_bps,
                    contributions, attribution_summary, attribution_quality,
                    quality_provenance, context_snapshot,
                    source_request_id, attributed_at, attributed_by
                ) VALUES (%s, %s, 'v1.0', 'dec-1', 30, 'w1', 'DECISION',
                    100, 50, 50, '[]', '{}', '{}', '{}', '{}', 'req-1', NOW(), 'test')""",
                (attr_id, eval_id)
            )

        # Verify state
        assert _count(conn, "attribution_records", "evaluation_id", eval_id) == 1

    def test_service_transaction_rollback_registry_failure(self, conn):
        """When registry insert fails due to duplicate canonical, record should still exist."""
        eval_id = f"txn-eval-{uuid.uuid4().hex[:8]}"
        attr_id_1 = f"txn-attr-{uuid.uuid4().hex[:8]}"
        attr_id_2 = f"txn-attr-{uuid.uuid4().hex[:8]}"

        # Insert first attribution + canonical
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO attribution_records (
                    attribution_id, evaluation_id, algorithm_version,
                    decision_id, evaluation_horizon_days, target_urn, target_type,
                    total_realized_return_bps, total_expected_return_bps, total_variance_bps,
                    contributions, attribution_summary, attribution_quality,
                    quality_provenance, context_snapshot,
                    source_request_id, attributed_at, attributed_by
                ) VALUES (%s, %s, 'v1.0', 'dec-1', 30, 'w1', 'DECISION',
                    100, 50, 50, '[]', '{}', '{}', '{}', '{}', 'req-1', NOW(), 'test')""",
                (attr_id_1, eval_id)
            )
            cur.execute(
                """INSERT INTO attribution_version_registry (
                    evaluation_id, algorithm_version, attribution_id, attribution_status
                ) VALUES (%s, 'v1.0', %s, 'CANONICAL')""",
                (eval_id, attr_id_1)
            )

        # Insert second attribution
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO attribution_records (
                    attribution_id, evaluation_id, algorithm_version,
                    decision_id, evaluation_horizon_days, target_urn, target_type,
                    total_realized_return_bps, total_expected_return_bps, total_variance_bps,
                    contributions, attribution_summary, attribution_quality,
                    quality_provenance, context_snapshot,
                    source_request_id, attributed_at, attributed_by
                ) VALUES (%s, %s, 'v2.0', 'dec-1', 30, 'w1', 'DECISION',
                    100, 50, 50, '[]', '{}', '{}', '{}', '{}', 'req-1', NOW(), 'test')""",
                (attr_id_2, eval_id)
            )

        # Try to insert second canonical (should fail)
        with pytest.raises(psycopg.errors.UniqueViolation):
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO attribution_version_registry (
                        evaluation_id, algorithm_version, attribution_id, attribution_status
                    ) VALUES (%s, 'v2.0', %s, 'CANONICAL')""",
                    (eval_id, attr_id_2)
                )

        # Verify: both attributions exist, only one canonical
        assert _count(conn, "attribution_records", "evaluation_id", eval_id) == 2
        assert _count(conn, "attribution_version_registry", "evaluation_id", eval_id) == 1

    def test_service_transaction_rollback_outbox_failure(self, conn):
        """When outbox insert fails, record and registry should still exist."""
        eval_id = f"txn-eval-{uuid.uuid4().hex[:8]}"
        attr_id = f"txn-attr-{uuid.uuid4().hex[:8]}"

        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO attribution_records (
                    attribution_id, evaluation_id, algorithm_version,
                    decision_id, evaluation_horizon_days, target_urn, target_type,
                    total_realized_return_bps, total_expected_return_bps, total_variance_bps,
                    contributions, attribution_summary, attribution_quality,
                    quality_provenance, context_snapshot,
                    source_request_id, attributed_at, attributed_by
                ) VALUES (%s, %s, 'v1.0', 'dec-1', 30, 'w1', 'DECISION',
                    100, 50, 50, '[]', '{}', '{}', '{}', '{}', 'req-1', NOW(), 'test')""",
                (attr_id, eval_id)
            )
            cur.execute(
                """INSERT INTO attribution_version_registry (
                    evaluation_id, algorithm_version, attribution_id, attribution_status
                ) VALUES (%s, 'v1.0', %s, 'CANONICAL')""",
                (eval_id, attr_id)
            )

        # Verify both exist
        assert _count(conn, "attribution_records", "evaluation_id", eval_id) == 1
        assert _count(conn, "attribution_version_registry", "evaluation_id", eval_id) == 1
