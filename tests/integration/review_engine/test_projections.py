"""Projection rebuild tests — Sprint-10 Wave-6."""
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
        cur.execute("DELETE FROM review_assessments WHERE review_id LIKE 'proj-%'")
        cur.execute("ALTER TABLE review_assessments ENABLE TRIGGER ALL")
        cur.execute("DELETE FROM review_version_registry WHERE review_id LIKE 'proj-%'")
        cur.execute("DELETE FROM worker_review_projection WHERE target_urn LIKE 'proj-%'")
        cur.execute("DELETE FROM thesis_review_projection WHERE thesis_urn LIKE 'proj-%'")
        cur.execute("DELETE FROM capability_gap_projection WHERE target_urn LIKE 'proj-%'")
        cur.execute("DELETE FROM review_coverage_projection")


def _insert_assessment(conn, review_id, evaluation_id, review_type="WORKER",
                       review_version="v1.0", findings=None):
    if findings is None:
        findings = [
            {"finding_id": "f1", "dimension": "THESIS", "finding_type": "OBSERVATION",
             "severity": "MEDIUM", "description": "Test finding", "confidence": 0.7,
             "created_at": datetime.utcnow().isoformat()}
        ]
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO review_assessments (
                review_id, evaluation_id, review_type, review_version,
                target_urn, target_type, decision_id, attribution_id,
                findings, recommendations, review_summary, review_quality,
                context_snapshot, reviewed_at, reviewed_by
            ) VALUES (%s, %s, %s, %s, 'proj-target', 'WORKER', 'proj-dec', 'proj-attr',
                %s, '{}', %s, %s, '{}', NOW(), 'test')""",
            (review_id, evaluation_id, review_type, review_version,
             json.dumps(findings),
             json.dumps({"total_findings": len(findings), "overall_assessment": "NEUTRAL", "confidence": 0.7}),
             json.dumps({"quality_score": 0.7, "data_completeness": 1.0, "analysis_depth": 0.8}))
        )


def _insert_registry(conn, evaluation_id, review_type, review_version, review_id, status="CANONICAL"):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO review_version_registry (
                evaluation_id, review_type, review_version, review_id, review_status
            ) VALUES (%s, %s, %s, %s, %s)""",
            (evaluation_id, review_type, review_version, review_id, status)
        )


from karsa.review_engine.application.review_projection_service import ReviewProjectionService


class TestWorkerReviewProjection:
    def test_rebuild(self, conn):
        _insert_assessment(conn, "proj-wr-1", "proj-we-1", "WORKER")
        _insert_registry(conn, "proj-we-1", "WORKER", "v1.0", "proj-wr-1")

        service = ReviewProjectionService(None)
        with conn.cursor() as cur:
            result = service._rebuild_worker_reviews(cur)

        assert result >= 1

    def test_canonical_filtering(self, conn):
        _insert_assessment(conn, "proj-wr-can", "proj-we-can", "WORKER")
        _insert_registry(conn, "proj-we-can", "WORKER", "v1.0", "proj-wr-can", "CANONICAL")

        _insert_assessment(conn, "proj-wr-sup", "proj-we-sup", "WORKER")
        _insert_registry(conn, "proj-we-sup", "WORKER", "v1.0", "proj-wr-sup", "SUPERSEDED")

        service = ReviewProjectionService(None)
        with conn.cursor() as cur:
            service._rebuild_worker_reviews(cur)
            cur.execute("SELECT COUNT(*) FROM worker_review_projection WHERE target_urn = 'proj-target'")
            count = cur.fetchone()[0]
            assert count == 1  # Only canonical

    def test_multiple_versions(self, conn):
        _insert_assessment(conn, "proj-wr-v1", "proj-we-mv", "WORKER", "v1.0")
        _insert_registry(conn, "proj-we-mv", "WORKER", "v1.0", "proj-wr-v1", "SUPERSEDED")

        _insert_assessment(conn, "proj-wr-v2", "proj-we-mv", "WORKER", "v2.0")
        _insert_registry(conn, "proj-we-mv", "WORKER", "v2.0", "proj-wr-v2", "CANONICAL")

        service = ReviewProjectionService(None)
        with conn.cursor() as cur:
            result = service._rebuild_worker_reviews(cur)
            assert result >= 1


class TestThesisReviewProjection:
    def test_rebuild(self, conn):
        _insert_assessment(conn, "proj-tr-1", "proj-te-1", "THESIS")
        _insert_registry(conn, "proj-te-1", "THESIS", "v1.0", "proj-tr-1")

        service = ReviewProjectionService(None)
        with conn.cursor() as cur:
            result = service._rebuild_thesis_reviews(cur)

        assert result >= 1


class TestCapabilityGapProjection:
    def test_rebuild(self, conn):
        findings = [
            {"finding_id": "f1", "dimension": "THESIS", "finding_type": "RISK",
             "severity": "HIGH", "description": "Risk finding", "confidence": 0.8,
             "created_at": datetime.utcnow().isoformat()},
            {"finding_id": "f2", "dimension": "EXECUTION", "finding_type": "OBSERVATION",
             "severity": "LOW", "description": "Observation", "confidence": 0.9,
             "created_at": datetime.utcnow().isoformat()},
        ]
        _insert_assessment(conn, "proj-cg-1", "proj-cg-e1", "WORKER", findings=findings)
        _insert_registry(conn, "proj-cg-e1", "WORKER", "v1.0", "proj-cg-1")

        service = ReviewProjectionService(None)
        with conn.cursor() as cur:
            result = service._rebuild_capability_gaps(cur)

        assert result == 1  # Only RISK finding included

    def test_concern_included(self, conn):
        findings = [
            {"finding_id": "f1", "dimension": "THESIS", "finding_type": "CONCERN",
             "severity": "MEDIUM", "description": "Concern finding", "confidence": 0.7,
             "created_at": datetime.utcnow().isoformat()},
        ]
        _insert_assessment(conn, "proj-cg-con", "proj-cg-e-con", "WORKER", findings=findings)
        _insert_registry(conn, "proj-cg-e-con", "WORKER", "v1.0", "proj-cg-con")

        service = ReviewProjectionService(None)
        with conn.cursor() as cur:
            result = service._rebuild_capability_gaps(cur)
            assert result == 1

    def test_observation_excluded(self, conn):
        findings = [
            {"finding_id": "f1", "dimension": "THESIS", "finding_type": "OBSERVATION",
             "severity": "LOW", "description": "Observation", "confidence": 0.9,
             "created_at": datetime.utcnow().isoformat()},
        ]
        _insert_assessment(conn, "proj-cg-obs", "proj-cg-e-obs", "WORKER", findings=findings)
        _insert_registry(conn, "proj-cg-e-obs", "WORKER", "v1.0", "proj-cg-obs")

        service = ReviewProjectionService(None)
        with conn.cursor() as cur:
            result = service._rebuild_capability_gaps(cur)
            assert result == 0  # OBSERVATION excluded


class TestReviewCoverageProjection:
    def test_rebuild(self, conn):
        _insert_assessment(conn, "proj-rc-1", "proj-rce-1", "WORKER")
        _insert_registry(conn, "proj-rce-1", "WORKER", "v1.0", "proj-rc-1")

        service = ReviewProjectionService(None)
        with conn.cursor() as cur:
            result = service._rebuild_review_coverage(cur)

        assert result >= 1

    def test_superseded_excluded(self, conn):
        _insert_assessment(conn, "proj-rc-sup", "proj-rce-sup", "WORKER")
        _insert_registry(conn, "proj-rce-sup", "WORKER", "v1.0", "proj-rc-sup", "SUPERSEDED")

        service = ReviewProjectionService(None)
        with conn.cursor() as cur:
            result = service._rebuild_review_coverage(cur)
            assert result == 0  # Superseded excluded


class TestProjectionRebuild:
    def test_deterministic_rebuild(self, conn):
        _insert_assessment(conn, "proj-det-1", "proj-det-e1", "WORKER")
        _insert_registry(conn, "proj-det-e1", "WORKER", "v1.0", "proj-det-1")

        service = ReviewProjectionService(None)

        # First rebuild
        with conn.cursor() as cur:
            result1 = service._rebuild_worker_reviews(cur)
        with conn.cursor() as cur:
            cur.execute("SELECT total_reviews FROM worker_review_projection")
            first = cur.fetchone()

        # Second rebuild
        with conn.cursor() as cur:
            result2 = service._rebuild_worker_reviews(cur)
        with conn.cursor() as cur:
            cur.execute("SELECT total_reviews FROM worker_review_projection")
            second = cur.fetchone()

        assert first[0] == second[0]

    def test_empty_source(self, conn):
        service = ReviewProjectionService(None)
        with conn.cursor() as cur:
            result = service._rebuild_worker_reviews(cur)
        assert result == 0

    def test_truncate_rebuild(self, conn):
        _insert_assessment(conn, "proj-tr-1", "proj-tr-e1", "WORKER")
        _insert_registry(conn, "proj-tr-e1", "WORKER", "v1.0", "proj-tr-1")

        service = ReviewProjectionService(None)

        # First rebuild
        with conn.cursor() as cur:
            service._rebuild_worker_reviews(cur)

        # Verify data exists
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM worker_review_projection")
            assert cur.fetchone()[0] >= 1

        # Second rebuild should truncate and recreate
        with conn.cursor() as cur:
            result = service._rebuild_worker_reviews(cur)
            assert result >= 1


class TestFailureTests:
    def test_malformed_findings_json(self, conn):
        """Malformed JSON in findings fails at INSERT time (database-level validation)."""
        with pytest.raises(psycopg.errors.InvalidTextRepresentation):
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO review_assessments (
                        review_id, evaluation_id, review_type, review_version,
                        target_urn, target_type, decision_id, attribution_id,
                        findings, recommendations, review_summary, review_quality,
                        context_snapshot, reviewed_at, reviewed_by
                    ) VALUES ('proj-mal-1', 'proj-mal-e1', 'WORKER', 'v1.0',
                        'proj-target', 'WORKER', 'proj-dec', 'proj-attr',
                        'not valid json', '{}', '{}', '{}', '{}', NOW(), 'test')
                    """
                )

    def test_missing_review_quality(self, conn):
        """Missing review_quality fails at INSERT time (database NOT NULL constraint)."""
        with pytest.raises(psycopg.errors.NotNullViolation):
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO review_assessments (
                        review_id, evaluation_id, review_type, review_version,
                        target_urn, target_type, decision_id, attribution_id,
                        findings, recommendations, review_summary, review_quality,
                        context_snapshot, reviewed_at, reviewed_by
                    ) VALUES ('proj-mq-1', 'proj-mq-e1', 'WORKER', 'v1.0',
                        'proj-target', 'WORKER', 'proj-dec', 'proj-attr',
                        '[]', '{}', '{}', NULL, '{}', NOW(), 'test')
                    """
                )
