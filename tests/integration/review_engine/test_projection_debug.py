"""Debug test for projection rebuild — Sprint-10 Wave-6."""
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


class TestProjectionDebug:
    def test_insert_and_query(self, conn):
        """Insert data and immediately query to verify availability."""
        with conn.cursor() as cur:
            # Disable trigger for insert
            cur.execute("ALTER TABLE review_assessments DISABLE TRIGGER ALL")
            cur.execute(
                """INSERT INTO review_assessments (
                    review_id, evaluation_id, review_type, review_version,
                    target_urn, target_type, decision_id, attribution_id,
                    findings, recommendations, review_summary, review_quality,
                    context_snapshot, reviewed_at, reviewed_by
                ) VALUES ('proj-debug-1', 'proj-deb-e1', 'WORKER', 'v1.0',
                    'proj-target', 'WORKER', 'proj-dec', 'proj-attr',
                    '[{\"finding_id\": \"f1\", \"finding_type\": \"RISK\"}]'::jsonb,
                    '{}', '{}', '{\"quality_score\": 0.7}', '{}', NOW(), 'test')
                """
            )
            cur.execute(
                """INSERT INTO review_version_registry (
                    evaluation_id, review_type, review_version, review_id, review_status
                ) VALUES ('proj-deb-e1', 'WORKER', 'v1.0', 'proj-debug-1', 'CANONICAL')
                """
            )
            cur.execute("ALTER TABLE review_assessments ENABLE TRIGGER ALL")

            # Immediately query
            cur.execute("""
                SELECT r.target_urn,
                       COUNT(*) as total_reviews,
                       SUM(jsonb_array_length(r.findings)) as total_findings
                FROM review_assessments r
                JOIN review_version_registry v ON v.review_id = r.review_id
                WHERE v.review_status = 'CANONICAL'
                  AND r.review_type = 'WORKER'
                GROUP BY r.target_urn
            """)
            row = cur.fetchone()
            assert row is not None
            assert row[2] == 1  # total_findings

    def test_projection_service_works(self, conn):
        """Test that the projection service can execute the rebuild."""
        from karsa.review_engine.application.review_projection_service import ReviewProjectionService

        # Insert test data
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE review_assessments DISABLE TRIGGER ALL")
            cur.execute(
                """INSERT INTO review_assessments (
                    review_id, evaluation_id, review_type, review_version,
                    target_urn, target_type, decision_id, attribution_id,
                    findings, recommendations, review_summary, review_quality,
                    context_snapshot, reviewed_at, reviewed_by
                ) VALUES ('proj-svc-1', 'proj-svc-e1', 'WORKER', 'v1.0',
                    'proj-target', 'WORKER', 'proj-dec', 'proj-attr',
                    '[{\"finding_id\": \"f1\", \"finding_type\": \"RISK\"}]'::jsonb,
                    '{}', '{}', '{\"quality_score\": 0.7}', '{}', NOW(), 'test')
                """
            )
            cur.execute(
                """INSERT INTO review_version_registry (
                    evaluation_id, review_type, review_version, review_id, review_status
                ) VALUES ('proj-svc-e1', 'WORKER', 'v1.0', 'proj-svc-1', 'CANONICAL')
                """
            )
            cur.execute("ALTER TABLE review_assessments ENABLE TRIGGER ALL")

        # Run projection rebuild
        service = ReviewProjectionService(None)
        with conn.cursor() as cur:
            result = service._rebuild_worker_reviews(cur)
            assert result >= 1
