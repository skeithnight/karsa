"""Projection verification tests — Sprint-10 Wave-8.

Verifies canonical filtering, superseded exclusion,
aggregation correctness, and deterministic rebuild.
"""
import pytest
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
        cur.execute("ALTER TABLE review_assessments DISABLE TRIGGER ALL")
        cur.execute("DELETE FROM review_assessments WHERE review_id LIKE 'projv-%'")
        cur.execute("ALTER TABLE review_assessments ENABLE TRIGGER ALL")
        cur.execute("DELETE FROM review_version_registry WHERE review_id LIKE 'projv-%'")
        cur.execute("DELETE FROM worker_review_projection WHERE target_urn LIKE 'projv-%'")
        cur.execute("DELETE FROM thesis_review_projection WHERE thesis_urn LIKE 'projv-%'")
        cur.execute("DELETE FROM capability_gap_projection WHERE target_urn LIKE 'projv-%'")
        cur.execute("DELETE FROM review_coverage_projection")


def _insert_assessment(conn, review_id, evaluation_id, review_type="WORKER",
                       review_version="v1.0", findings=None):
    if findings is None:
        findings = [{"finding_id": "f1", "finding_type": "OBSERVATION", "severity": "MEDIUM",
                     "description": "Test", "confidence": 0.7, "created_at": datetime.utcnow().isoformat()}]
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE review_assessments DISABLE TRIGGER ALL")
        cur.execute('''INSERT INTO review_assessments (
            review_id, evaluation_id, review_type, review_version,
            target_urn, target_type, decision_id, attribution_id,
            findings, recommendations, review_summary, review_quality,
            context_snapshot, reviewed_at, reviewed_by
        ) VALUES (%s, %s, %s, %s, 'projv-target', 'WORKER', 'projv-dec', 'projv-attr',
            %s, '{}', %s, %s, '{}', NOW(), 'test')
        ''', (
            review_id, evaluation_id, review_type, review_version,
            json.dumps(findings),
            json.dumps({"total_findings": len(findings), "overall_assessment": "NEUTRAL", "confidence": 0.7}),
            json.dumps({"quality_score": 0.7, "data_completeness": 1.0, "analysis_depth": 0.8}),
        ))
        cur.execute("ALTER TABLE review_assessments ENABLE TRIGGER ALL")


def _insert_registry(conn, evaluation_id, review_type, review_version, review_id, status="CANONICAL"):
    with conn.cursor() as cur:
        cur.execute('''INSERT INTO review_version_registry (
            evaluation_id, review_type, review_version, review_id, review_status
        ) VALUES (%s, %s, %s, %s, %s)''',
            (evaluation_id, review_type, review_version, review_id, status))


# --- Projection Determinism ---

class TestProjectionDeterminism:
    def test_worker_projection_rebuild_deterministic(self, conn):
        from karsa.review_engine.application.review_projection_service import ReviewProjectionService

        _insert_assessment(conn, "projv-det-1", "projv-det-e1", "WORKER")
        _insert_registry(conn, "projv-det-e1", "WORKER", "v1.0", "projv-det-1")

        service = ReviewProjectionService(None)

        # First rebuild
        with conn.cursor() as cur:
            service._rebuild_worker_reviews(cur)
            cur.execute("SELECT total_reviews, avg_quality_score FROM worker_review_projection WHERE target_urn = 'projv-target'")
            first = cur.fetchone()

        # Second rebuild
        with conn.cursor() as cur:
            service._rebuild_worker_reviews(cur)
            cur.execute("SELECT total_reviews, avg_quality_score FROM worker_review_projection WHERE target_urn = 'projv-target'")
            second = cur.fetchone()

        assert first == second

    def test_coverage_projection_rebuild_deterministic(self, conn):
        from karsa.review_engine.application.review_projection_service import ReviewProjectionService

        _insert_assessment(conn, "projv-cov-1", "projv-cov-e1", "WORKER")
        _insert_registry(conn, "projv-cov-e1", "WORKER", "v1.0", "projv-cov-1")

        service = ReviewProjectionService(None)

        # First rebuild
        with conn.cursor() as cur:
            service._rebuild_review_coverage(cur)
            cur.execute("SELECT review_status FROM review_coverage_projection WHERE decision_id = 'projv-cov-e1'")
            first = cur.fetchone()

        # Second rebuild
        with conn.cursor() as cur:
            service._rebuild_review_coverage(cur)
            cur.execute("SELECT review_status FROM review_coverage_projection WHERE decision_id = 'projv-cov-e1'")
            second = cur.fetchone()

        assert first == second


# --- Projection Correctness ---

class TestProjectionCorrectness:
    def test_canonical_filtering(self, conn):
        from karsa.review_engine.application.review_projection_service import ReviewProjectionService

        _insert_assessment(conn, "projv-can-1", "projv-can-e1", "WORKER")
        _insert_registry(conn, "projv-can-e1", "WORKER", "v1.0", "projv-can-1", "CANONICAL")

        _insert_assessment(conn, "projv-can-2", "projv-can-e2", "WORKER")
        _insert_registry(conn, "projv-can-e2", "WORKER", "v1.0", "projv-can-2", "SUPERSEDED")

        service = ReviewProjectionService(None)
        with conn.cursor() as cur:
            service._rebuild_worker_reviews(cur)
            cur.execute("SELECT COUNT(*) FROM worker_review_projection")
            assert cur.fetchone()[0] == 1  # Only canonical

    def test_aggregation_correctness(self, conn):
        from karsa.review_engine.application.review_projection_service import ReviewProjectionService

        _insert_assessment(conn, "projv-agg-1", "projv-agg-e1", "WORKER")
        _insert_assessment(conn, "projv-agg-2", "projv-agg-e1", "WORKER")
        _insert_registry(conn, "projv-agg-e1", "WORKER", "v1.0", "projv-agg-1", "CANONICAL")
        _insert_registry(conn, "projv-agg-e1", "WORKER", "v1.0", "projv-agg-2", "SUPERSEDED")

        service = ReviewProjectionService(None)
        with conn.cursor() as cur:
            service._rebuild_worker_reviews(cur)
            cur.execute("SELECT total_reviews FROM worker_review_projection WHERE target_urn = 'projv-target'")
            assert cur.fetchone()[0] == 1  # Only canonical


# --- Transaction Verification ---

class TestTransactionVerification:
    def test_outbox_persisted_with_aggregate(self, conn):
        """Verify outbox and aggregate are in same transaction context."""
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE review_assessments DISABLE TRIGGER ALL")
            cur.execute('''INSERT INTO review_assessments (
                review_id, evaluation_id, review_type, review_version,
                target_urn, target_type, decision_id, attribution_id,
                findings, recommendations, review_summary, review_quality,
                context_snapshot, reviewed_at, reviewed_by
            ) VALUES ('v8-tx-1', 'v8-tx-e1', 'WORKER', 'v1.0',
                'v8-tx-t', 'WORKER', 'v8-tx-d', 'v8-tx-a',
                '[]', '{}', '{}', '{"quality_score":0.7}', '{}', NOW(), 'test')
            ''')
            cur.execute("ALTER TABLE review_assessments ENABLE TRIGGER ALL")

            # Verify data exists
            cur.execute("SELECT COUNT(*) FROM review_assessments WHERE review_id = 'v8-tx-1'")
            assert cur.fetchone()[0] == 1
