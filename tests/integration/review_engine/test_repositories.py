"""Repository integration tests — Sprint-10 Wave-3."""
import pytest
import uuid
import json
from datetime import datetime
import psycopg

from karsa.review_engine.domain.aggregates.review_assessment import ReviewAssessment
from karsa.review_engine.domain.entities.review_finding import ReviewFinding
from karsa.review_engine.domain.entities.review_recommendation import ReviewRecommendation
from karsa.review_engine.domain.value_objects.enums import (
    ReviewType, FindingType, FindingSeverity,
    RecommendationType, RecommendationPriority,
)
from karsa.review_engine.domain.value_objects.review_evidence import ReviewEvidence
from karsa.review_engine.domain.value_objects.review_summary import ReviewSummary
from karsa.review_engine.domain.value_objects.review_quality import ReviewQuality
from karsa.review_engine.domain.value_objects.review_context_snapshot import ReviewContextSnapshot
from karsa.review_engine.infrastructure.persistence.postgres_review_assessment_repository import PostgresReviewAssessmentRepository
from karsa.review_engine.infrastructure.persistence.postgres_version_registry_repository import PostgresReviewVersionRegistryRepository
from karsa.review_engine.infrastructure.persistence.postgres_review_outbox_repository import PostgresReviewOutboxRepository
from karsa.review_engine.infrastructure.repositories.review_version_registry_repository import VersionRegistryEntry
from karsa.review_engine.infrastructure.repositories.review_outbox_repository import OutboxEvent


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
        cur.execute("DELETE FROM review_assessments WHERE review_id LIKE 'repo-%'")
        cur.execute("ALTER TABLE review_assessments ENABLE TRIGGER ALL")
        cur.execute("DELETE FROM review_version_registry WHERE review_id LIKE 'repo-%'")
        cur.execute("DELETE FROM review_outbox WHERE outbox_id LIKE 'repo-%'")


def _make_finding(finding_id="f1"):
    return ReviewFinding(
        finding_id=finding_id,
        dimension="THESIS",
        finding_type=FindingType.OBSERVATION,
        severity=FindingSeverity.MEDIUM,
        description="Test finding",
        evidence=ReviewEvidence(source_type="TEST", source_id="e1", data_points={}, explanation="test"),
        confidence=0.7,
        created_at=datetime.utcnow().isoformat(),
    )


def _make_recommendation(rec_id="r1", finding_id="f1"):
    return ReviewRecommendation(
        recommendation_id=rec_id,
        finding_id=finding_id,
        recommendation_type=RecommendationType.ADJUST_ALLOCATION,
        priority=RecommendationPriority.MEDIUM,
        description="Test recommendation",
        expected_impact="Improved returns",
        implementation_risk="Low",
        created_at=datetime.utcnow().isoformat(),
    )


def _make_assessment(review_id="repo-review-1", evaluation_id="repo-eval-1",
                     review_type=ReviewType.WORKER, review_version="v1.0"):
    return ReviewAssessment(
        review_id=review_id,
        evaluation_id=evaluation_id,
        review_type=review_type,
        review_version=review_version,
        target_urn="worker-1",
        target_type="WORKER",
        decision_id="dec-1",
        attribution_id="attr-1",
        findings=[_make_finding()],
        recommendations=[_make_recommendation()],
        review_summary=ReviewSummary(
            total_findings=1, findings_by_severity={"MEDIUM": 1},
            total_recommendations=1, recommendations_by_priority={"MEDIUM": 1},
            overall_assessment="NEUTRAL", confidence=0.7, explanation="test",
        ),
        review_quality=ReviewQuality(quality_score=0.7, data_completeness=1.0, analysis_depth=0.8),
        context_snapshot=ReviewContextSnapshot(
            evaluation_snapshot={"id": "eval-1"},
            decision_snapshot={"id": "dec-1"},
            snapshot_hash="abc123",
        ),
        reviewed_at=datetime.utcnow(),
        reviewed_by="test",
    )


# --- ReviewAssessmentRepository Tests ---

class TestReviewAssessmentRepository:
    def test_save_and_retrieve(self, conn):
        repo = PostgresReviewAssessmentRepository(conn)
        assessment = _make_assessment()
        inserted = repo.save(assessment)
        assert inserted is True
        result = repo.get_by_id("repo-review-1")
        assert result is not None
        assert result.review_id == "repo-review-1"
        assert result.evaluation_id == "repo-eval-1"

    def test_jsonb_roundtrip(self, conn):
        repo = PostgresReviewAssessmentRepository(conn)
        assessment = _make_assessment(review_id="repo-review-jb")
        repo.save(assessment)
        result = repo.get_by_id("repo-review-jb")
        assert result is not None
        assert len(result.findings) == 1
        assert result.findings[0].finding_id == "f1"
        assert len(result.recommendations) == 1
        assert result.recommendations[0].recommendation_id == "r1"
        assert result.review_summary.total_findings == 1
        assert result.review_quality.quality_score == 0.7

    def test_duplicate_identity_rejected(self, conn):
        repo = PostgresReviewAssessmentRepository(conn)
        assessment1 = _make_assessment(review_id="repo-dup-1")
        assessment2 = _make_assessment(review_id="repo-dup-2")  # same eval/type/version
        assert repo.save(assessment1) is True
        assert repo.save(assessment2) is False  # ON CONFLICT DO NOTHING

    def test_get_by_evaluation_and_type(self, conn):
        repo = PostgresReviewAssessmentRepository(conn)
        assessment = _make_assessment(review_id="repo-eval-type-1", evaluation_id="eval-type-1")
        repo.save(assessment)
        result = repo.get_by_evaluation_and_type("eval-type-1", "WORKER")
        assert result is not None
        assert result.review_id == "repo-eval-type-1"

    def test_get_by_target_urn(self, conn):
        repo = PostgresReviewAssessmentRepository(conn)
        repo.save(_make_assessment(review_id="repo-target-1", evaluation_id="eval-target-1"))
        repo.save(_make_assessment(review_id="repo-target-2", evaluation_id="eval-target-2"))
        results = repo.get_by_target_urn("worker-1")
        assert len(results) >= 2

    def test_pagination(self, conn):
        repo = PostgresReviewAssessmentRepository(conn)
        for i in range(5):
            repo.save(_make_assessment(review_id=f"repo-page-{i}", evaluation_id=f"eval-page-{i}"))
        page1 = repo.list_reviews(page=1, size=2)
        assert len(page1) == 2

    def test_domain_reconstruction(self, conn):
        repo = PostgresReviewAssessmentRepository(conn)
        assessment = _make_assessment(review_id="repo-recon-1")
        repo.save(assessment)
        result = repo.get_by_id("repo-recon-1")
        assert result.review_type == ReviewType.WORKER
        assert result.findings[0].finding_type == FindingType.OBSERVATION
        assert result.findings[0].severity == FindingSeverity.MEDIUM
        assert result.recommendations[0].recommendation_type == RecommendationType.ADJUST_ALLOCATION


# --- ReviewVersionRegistryRepository Tests ---

class TestReviewVersionRegistryRepository:
    def test_save_and_get_canonical(self, conn):
        # First create the assessment that the registry references
        assessment_repo = PostgresReviewAssessmentRepository(conn)
        assessment_repo.save(_make_assessment(review_id="repo-review-reg-1", evaluation_id="repo-reg-1"))

        repo = PostgresReviewVersionRegistryRepository(conn)
        entry = VersionRegistryEntry(
            version_id=str(uuid.uuid4()),
            evaluation_id="repo-reg-1",
            review_type="WORKER",
            review_version="v1.0",
            review_id="repo-review-reg-1",
            review_status="CANONICAL",
            superseded_by=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        repo.save(entry)
        result = repo.get_canonical("repo-reg-1", "WORKER")
        assert result is not None
        assert result.review_status == "CANONICAL"

    def test_supersede_previous(self, conn):
        assessment_repo = PostgresReviewAssessmentRepository(conn)
        assessment_repo.save(_make_assessment(review_id="repo-review-sup-1", evaluation_id="repo-sup-1"))
        assessment_repo.save(_make_assessment(review_id="repo-review-sup-2", evaluation_id="repo-sup-1", review_version="v2.0"))

        repo = PostgresReviewVersionRegistryRepository(conn)
        entry1 = VersionRegistryEntry(
            version_id=str(uuid.uuid4()),
            evaluation_id="repo-sup-1",
            review_type="WORKER",
            review_version="v1.0",
            review_id="repo-review-sup-1",
            review_status="CANONICAL",
            superseded_by=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        repo.save(entry1)
        repo.supersede_previous("repo-sup-1", "WORKER", "repo-review-sup-2")
        result = repo.get_canonical("repo-sup-1", "WORKER")
        assert result is None  # superseded, no canonical

    def test_list_by_evaluation(self, conn):
        assessment_repo = PostgresReviewAssessmentRepository(conn)
        for i in range(3):
            assessment_repo.save(_make_assessment(
                review_id=f"repo-review-list-{i}",
                evaluation_id="repo-list-1",
                review_version=f"v{i}.0",
            ))

        repo = PostgresReviewVersionRegistryRepository(conn)
        for i in range(3):
            entry = VersionRegistryEntry(
                version_id=str(uuid.uuid4()),
                evaluation_id="repo-list-1",
                review_type="WORKER",
                review_version=f"v{i}.0",
                review_id=f"repo-review-list-{i}",
                review_status="SUPERSEDED" if i < 2 else "CANONICAL",
                superseded_by=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            repo.save(entry)
        results = repo.list_by_evaluation("repo-list-1")
        assert len(results) == 3


# --- ReviewOutboxRepository Tests ---

class TestReviewOutboxRepository:
    def test_save_and_get_pending(self, conn):
        repo = PostgresReviewOutboxRepository(conn)
        event = OutboxEvent(
            outbox_id="repo-out-1",
            event_type="TestEvent",
            payload='{"key": "value"}',
            aggregate_id="agg-1",
            status="PENDING",
            created_at=datetime.utcnow(),
        )
        repo.save_event(event)
        pending = repo.get_pending()
        assert len(pending) >= 1
        assert any(e.outbox_id == "repo-out-1" for e in pending)

    def test_mark_sent(self, conn):
        repo = PostgresReviewOutboxRepository(conn)
        event = OutboxEvent(
            outbox_id="repo-out-sent",
            event_type="TestEvent",
            payload='{}',
            aggregate_id="agg-2",
            status="PENDING",
            created_at=datetime.utcnow(),
        )
        repo.save_event(event)
        now = datetime.utcnow()
        repo.mark_sent("repo-out-sent", now)
        pending = repo.get_pending()
        assert not any(e.outbox_id == "repo-out-sent" for e in pending)

    def test_mark_failed(self, conn):
        repo = PostgresReviewOutboxRepository(conn)
        event = OutboxEvent(
            outbox_id="repo-out-fail",
            event_type="TestEvent",
            payload='{}',
            aggregate_id="agg-3",
            status="PENDING",
            created_at=datetime.utcnow(),
        )
        repo.save_event(event)
        repo.mark_failed("repo-out-fail")
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM review_outbox WHERE outbox_id = 'repo-out-fail'")
            assert cur.fetchone()[0] == "FAILED"
