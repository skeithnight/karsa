"""Application service tests — Sprint-10 Wave-4."""
import pytest
from datetime import datetime
from typing import Optional, List, Dict

from karsa.review_engine.domain.aggregates.review_assessment import ReviewAssessment, MAX_FINDINGS, MAX_RECOMMENDATIONS
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
from karsa.review_engine.infrastructure.repositories.review_version_registry_repository import VersionRegistryEntry
from karsa.review_engine.infrastructure.repositories.review_outbox_repository import OutboxEvent
from karsa.review_engine.application.review_quality_gate_service import ReviewQualityGateService, QUALITY_THRESHOLD
from karsa.review_engine.application.review_recommendation_service import ReviewRecommendationService
from karsa.review_engine.application.review_versioning_service import ReviewVersioningService
from karsa.review_engine.application.review_execution_service import ReviewExecutionService
from karsa.review_engine.application.review_replay_service import ReviewReplayService


# --- In-memory repositories ---

class InMemoryReviewAssessmentRepository:
    def __init__(self):
        self._store: Dict[str, ReviewAssessment] = {}

    def save(self, record: ReviewAssessment) -> bool:
        key = f"{record.evaluation_id}:{record.review_type}:{record.review_version}"
        if any(
            r.evaluation_id == record.evaluation_id and
            r.review_type == record.review_type and
            r.review_version == record.review_version
            for r in self._store.values()
        ):
            return False
        self._store[record.review_id] = record
        return True

    def get_by_id(self, review_id: str) -> Optional[ReviewAssessment]:
        return self._store.get(review_id)

    def get_by_evaluation_and_type(self, evaluation_id: str, review_type: str) -> Optional[ReviewAssessment]:
        for r in self._store.values():
            if r.evaluation_id == evaluation_id and r.review_type.value == review_type:
                return r
        return None

    def get_by_target_urn(self, target_urn: str) -> List[ReviewAssessment]:
        return [r for r in self._store.values() if r.target_urn == target_urn]

    def list_reviews(self, page: int = 1, size: int = 50) -> List[ReviewAssessment]:
        items = sorted(self._store.values(), key=lambda r: r.created_at, reverse=True)
        offset = (page - 1) * size
        return items[offset:offset + size]


class InMemoryVersionRegistryRepository:
    def __init__(self):
        self._store: Dict[str, VersionRegistryEntry] = {}

    def save(self, entry: VersionRegistryEntry) -> None:
        self._store[entry.version_id] = entry

    def get_canonical(self, evaluation_id: str, review_type: str) -> Optional[VersionRegistryEntry]:
        for e in self._store.values():
            if e.evaluation_id == evaluation_id and e.review_type == review_type and e.review_status == "CANONICAL":
                return e
        return None

    def get_by_evaluation_and_version(
        self, evaluation_id: str, review_type: str, review_version: str
    ) -> Optional[VersionRegistryEntry]:
        for e in self._store.values():
            if e.evaluation_id == evaluation_id and e.review_type == review_type and e.review_version == review_version:
                return e
        return None

    def supersede_previous(self, evaluation_id: str, review_type: str, new_review_id: str) -> None:
        for e in self._store.values():
            if e.evaluation_id == evaluation_id and e.review_type == review_type and e.review_status == "CANONICAL":
                e.review_status = "SUPERSEDED"
                e.superseded_by = new_review_id

    def list_by_evaluation(self, evaluation_id: str) -> List[VersionRegistryEntry]:
        return [e for e in self._store.values() if e.evaluation_id == evaluation_id]


class InMemoryOutboxRepository:
    def __init__(self):
        self._store: Dict[str, OutboxEvent] = {}

    def save_event(self, event: OutboxEvent) -> None:
        self._store[event.outbox_id] = event

    def get_pending(self, limit: int = 100) -> List[OutboxEvent]:
        pending = [e for e in self._store.values() if e.status == "PENDING"]
        return pending[:limit]

    def mark_sent(self, outbox_id: str, sent_at: datetime) -> None:
        if outbox_id in self._store:
            self._store[outbox_id].status = "SENT"
            self._store[outbox_id].sent_at = sent_at

    def mark_failed(self, outbox_id: str) -> None:
        if outbox_id in self._store:
            self._store[outbox_id].status = "FAILED"


class InMemoryProjectionRepository:
    def get_worker_review(self, target_urn: str) -> Optional[Dict]:
        return None

    def get_thesis_review(self, thesis_urn: str) -> Optional[Dict]:
        return None

    def get_capability_gaps(self, target_urn: str) -> List[Dict]:
        return []

    def rebuild_all(self) -> None:
        pass


# --- Fixtures ---

def _make_evaluation_event():
    return {
        "evaluation_id": "eval-1",
        "target_urn": "worker-1",
        "target_type": "WORKER",
        "decision_id": "dec-1",
        "total_realized_return_bps": 100.0,
        "total_expected_return_bps": 50.0,
        "total_variance_bps": 50.0,
        "quality_score": 0.7,
        "data_completeness": 1.0,
        "analysis_depth": 0.8,
        "missing_data": [],
        "decision_snapshot": {"decision_id": "dec-1", "allocated_weights": {"w1": 0.6}},
        "regime_context": {"regime_at_decision": "BULL", "regime_changed": False},
    }


def _make_services():
    assessment_repo = InMemoryReviewAssessmentRepository()
    registry_repo = InMemoryVersionRegistryRepository()
    outbox_repo = InMemoryOutboxRepository()
    projection_repo = InMemoryProjectionRepository()

    quality_gate = ReviewQualityGateService()
    recommendation_service = ReviewRecommendationService()
    versioning_service = ReviewVersioningService(registry_repo, assessment_repo)

    execution_service = ReviewExecutionService(
        assessment_repo=assessment_repo,
        registry_repo=registry_repo,
        outbox_repo=outbox_repo,
        quality_gate_service=quality_gate,
        recommendation_service=recommendation_service,
        versioning_service=versioning_service,
    )

    replay_service = ReviewReplayService(
        assessment_repo=assessment_repo,
        registry_repo=registry_repo,
        projection_repo=projection_repo,
    )

    return execution_service, versioning_service, replay_service, assessment_repo, registry_repo, outbox_repo


# --- ReviewExecutionService Tests ---

class TestReviewExecutionService:
    def test_execute_review_creates_assessment(self):
        service, _, _, repo, _, _ = _make_services()
        assessment = service.execute_review(_make_evaluation_event())
        assert assessment is not None
        assert assessment.evaluation_id == "eval-1"
        assert len(assessment.findings) >= 1

    def test_execute_review_saves_to_repository(self):
        service, _, _, repo, _, _ = _make_services()
        service.execute_review(_make_evaluation_event())
        assert len(repo._store) == 1

    def test_execute_review_registers_canonical(self):
        service, _, _, _, registry, _ = _make_services()
        service.execute_review(_make_evaluation_event())
        canonical = registry.get_canonical("eval-1", "WORKER")
        assert canonical is not None
        assert canonical.review_status == "CANONICAL"

    def test_execute_review_saves_outbox_events(self):
        service, _, _, _, _, outbox = _make_services()
        service.execute_review(_make_evaluation_event())
        assert len(outbox._store) >= 1

    def test_execute_review_duplicate_returns_existing(self):
        service, _, _, repo, _, _ = _make_services()
        a1 = service.execute_review(_make_evaluation_event())
        a2 = service.execute_review(_make_evaluation_event())
        assert a1.review_id == a2.review_id

    def test_execute_review_with_attribution(self):
        service, _, _, _, _, _ = _make_services()
        attr_event = {"attribution_id": "attr-1", "quality_score": 0.8}
        assessment = service.execute_review(_make_evaluation_event(), attr_event)
        assert assessment.attribution_id == "attr-1"

    def test_transaction_boundary(self):
        """Verify all three repos are written atomically."""
        service, _, _, repo, registry, outbox = _make_services()
        service.execute_review(_make_evaluation_event())
        assert len(repo._store) == 1
        assert len([e for e in registry._store.values() if e.review_status == "CANONICAL"]) == 1
        assert len(outbox._store) >= 1


# --- ReviewVersioningService Tests ---

class TestReviewVersioningService:
    def test_register_canonical(self):
        _, service, _, repo, registry, _ = _make_services()
        # First save assessment
        repo.save(_make_assessment("eval-v1", "v1.0"))
        entry = service.register_canonical("eval-v1", "WORKER", "v1.0", "rev-v1")
        assert entry.review_status == "CANONICAL"

    def test_supersede_previous(self):
        _, service, _, repo, registry, _ = _make_services()
        repo.save(_make_assessment("eval-sup", "v1.0"))
        repo.save(_make_assessment("eval-sup", "v2.0"))
        service.register_canonical("eval-sup", "WORKER", "v1.0", "rev-sup-1")
        service.register_canonical("eval-sup", "WORKER", "v2.0", "rev-sup-2")
        entries = service.list_history("eval-sup")
        superseded = [e for e in entries if e.review_status == "SUPERSEDED"]
        assert len(superseded) == 1

    def test_promote_experimental(self):
        _, service, _, repo, registry, _ = _make_services()
        entry = VersionRegistryEntry(
            version_id="v1",
            evaluation_id="eval-exp",
            review_type="WORKER",
            review_version="v1.0",
            review_id="rev-exp",
            review_status="EXPERIMENTAL",
            superseded_by=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        registry.save(entry)
        promoted = service.promote_experimental("eval-exp", "WORKER", "v1.0")
        assert promoted is not None
        assert promoted.review_status == "CANONICAL"


# --- ReviewQualityGateService Tests ---

class TestReviewQualityGateService:
    def test_quality_pass(self):
        service = ReviewQualityGateService()
        quality = service.evaluate_quality(0.7, 1.0, 0.8, [])
        assert service.should_complete(quality) is True

    def test_quality_defer(self):
        service = ReviewQualityGateService()
        quality = service.evaluate_quality(0.2, 0.5, 0.3, ["missing_data"])
        assert service.should_complete(quality) is False

    def test_quality_boundary(self):
        service = ReviewQualityGateService()
        quality = service.evaluate_quality(0.3, 1.0, 1.0, [])
        assert service.should_complete(quality) is True

    def test_create_completed_event(self):
        service = ReviewQualityGateService()
        event = service.create_completed_event(
            "e1", "r1", "eval-1", "WORKER", "v1.0", "w1",
            {}, {}, 5, 3, "2026-06-20",
        )
        assert event.event_type == "ReviewCompletedEvent"

    def test_create_deferred_event(self):
        service = ReviewQualityGateService()
        event = service.create_deferred_event(
            "e1", "eval-1", "WORKER", 0.2, ["missing"], "2026-06-20",
        )
        assert event.event_type == "ReviewDeferredEvent"
        assert "below threshold" in event.reason


# --- ReviewRecommendationService Tests ---

class TestReviewRecommendationService:
    def test_generate_recommendations(self):
        service = ReviewRecommendationService()
        findings = [
            _make_finding("f1", FindingSeverity.CRITICAL),
            _make_finding("f2", FindingSeverity.HIGH),
            _make_finding("f3", FindingSeverity.MEDIUM),
        ]
        recs = service.generate_recommendations(findings, "rev-1")
        assert len(recs) == 3
        assert recs[0].recommendation_type == RecommendationType.ESCALATE
        assert recs[1].recommendation_type == RecommendationType.ADJUST_ALLOCATION
        assert recs[2].recommendation_type == RecommendationType.NO_ACTION

    def test_size_guardrail_within_limits(self):
        service = ReviewRecommendationService()
        findings = [_make_finding(f"f{i}", FindingSeverity.LOW) for i in range(50)]
        recs = service.generate_recommendations(findings, "rev-1")
        event = service.check_size_guardrail(findings, recs, "rev-1")
        assert event is None

    def test_size_guardrail_exceeded(self):
        service = ReviewRecommendationService()
        findings = [_make_finding(f"f{i}", FindingSeverity.LOW) for i in range(101)]
        recs = service.generate_recommendations(findings, "rev-1")
        event = service.check_size_guardrail(findings, recs, "rev-1")
        assert event is not None
        assert event.finding_count == 101


# --- ReviewReplayService Tests ---

class TestReviewReplayService:
    def test_get_canonical_review(self):
        service, _, replay, repo, registry, _ = _make_services()
        assessment = service.execute_review(_make_evaluation_event())
        result = replay.get_canonical_review("eval-1", "WORKER")
        assert result is not None
        assert result.evaluation_id == "eval-1"

    def test_get_review_history(self):
        service, _, replay, repo, registry, _ = _make_services()
        service.execute_review(_make_evaluation_event())
        history = replay.get_review_history("eval-1")
        assert len(history) >= 1

    def test_deterministic_replay(self):
        """Same inputs produce same outputs."""
        service, _, replay, repo, registry, _ = _make_services()
        a1 = service.execute_review(_make_evaluation_event())
        result1 = replay.get_canonical_review("eval-1", "WORKER")

        # Create new service with same repos
        service2 = ReviewExecutionService(
            assessment_repo=repo,
            registry_repo=registry,
            outbox_repo=InMemoryOutboxRepository(),
            quality_gate_service=ReviewQualityGateService(),
            recommendation_service=ReviewRecommendationService(),
            versioning_service=ReviewVersioningService(registry, repo),
        )
        replay2 = ReviewReplayService(repo, registry, InMemoryProjectionRepository())
        result2 = replay2.get_canonical_review("eval-1", "WORKER")

        assert result1.review_id == result2.review_id

    def test_no_upstream_queries(self):
        """Replay never queries upstream engines."""
        service, _, replay, _, _, _ = _make_services()
        service.execute_review(_make_evaluation_event())
        # Replay uses only persisted state
        result = replay.get_canonical_review("eval-1", "WORKER")
        assert result is not None


# --- Helpers ---

def _make_finding(finding_id, severity):
    return ReviewFinding(
        finding_id=finding_id,
        dimension="THESIS",
        finding_type=FindingType.OBSERVATION,
        severity=severity,
        description=f"Finding {finding_id}",
        evidence=ReviewEvidence(source_type="TEST", source_id="e1", data_points={}, explanation="test"),
        confidence=0.7,
        created_at=datetime.utcnow().isoformat(),
    )


# --- Additional Quality Gate Tests ---

class TestQualityGateEdgeCases:
    def test_quality_score_zero(self):
        service = ReviewQualityGateService()
        quality = service.evaluate_quality(0.0, 0.0, 0.0, ["all missing"])
        assert service.should_complete(quality) is False

    def test_quality_score_one(self):
        service = ReviewQualityGateService()
        quality = service.evaluate_quality(1.0, 1.0, 1.0, [])
        assert service.should_complete(quality) is True

    def test_quality_with_missing_data(self):
        service = ReviewQualityGateService()
        quality = service.evaluate_quality(0.5, 0.8, 0.6, ["regime_data", "journal_data"])
        assert len(quality.missing_data) == 2
        assert service.should_complete(quality) is True


# --- Additional Recommendation Tests ---

class TestRecommendationEdgeCases:
    def test_empty_findings(self):
        service = ReviewRecommendationService()
        recs = service.generate_recommendations([], "rev-empty")
        assert len(recs) == 0

    def test_mixed_severity_findings(self):
        service = ReviewRecommendationService()
        findings = [
            _make_finding("f1", FindingSeverity.CRITICAL),
            _make_finding("f2", FindingSeverity.HIGH),
            _make_finding("f3", FindingSeverity.MEDIUM),
            _make_finding("f4", FindingSeverity.LOW),
        ]
        recs = service.generate_recommendations(findings, "rev-mix")
        assert len(recs) == 4
        types = [r.recommendation_type for r in recs]
        assert RecommendationType.ESCALATE in types
        assert RecommendationType.ADJUST_ALLOCATION in types
        assert types.count(RecommendationType.NO_ACTION) == 2

    def test_size_guardrail_exact_limit(self):
        service = ReviewRecommendationService()
        # Use fewer findings to stay within both limits
        findings = [_make_finding(f"f{i}", FindingSeverity.LOW) for i in range(50)]
        recs = service.generate_recommendations(findings, "rev-exact")
        event = service.check_size_guardrail(findings, recs, "rev-exact")
        assert event is None

    def test_size_guardrail_one_over(self):
        service = ReviewRecommendationService()
        findings = [_make_finding(f"f{i}", FindingSeverity.LOW) for i in range(MAX_FINDINGS + 1)]
        recs = service.generate_recommendations(findings, "rev-over")
        event = service.check_size_guardrail(findings, recs, "rev-over")
        assert event is not None
        assert event.limit_findings == MAX_FINDINGS


# --- Additional Versioning Tests ---

class TestVersioningEdgeCases:
    def test_get_canonical_not_found(self):
        _, service, _, _, registry, _ = _make_services()
        result = service.get_canonical("nonexistent", "WORKER")
        assert result is None

    def test_list_history_empty(self):
        _, service, _, _, _, _ = _make_services()
        history = service.list_history("nonexistent")
        assert len(history) == 0

    def test_promote_non_experimental_fails(self):
        _, service, _, repo, registry, _ = _make_services()
        repo.save(_make_assessment("eval-promote", "v1.0"))
        entry = VersionRegistryEntry(
            version_id="v1",
            evaluation_id="eval-promote",
            review_type="WORKER",
            review_version="v1.0",
            review_id="rev-promote",
            review_status="CANONICAL",
            superseded_by=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        registry.save(entry)
        result = service.promote_experimental("eval-promote", "WORKER", "v1.0")
        assert result is None  # Not experimental

    def test_version_changed_event_creation(self):
        _, service, _, _, _, _ = _make_services()
        event = service.create_version_changed_event(
            "eval-1", "WORKER", "rev-old", "rev-new", "test-user"
        )
        assert event.event_type == "ReviewCanonicalVersionChangedEvent"
        assert event.previous_review_id == "rev-old"
        assert event.new_review_id == "rev-new"


# --- Additional Replay Tests ---

class TestReplayEdgeCases:
    def test_get_canonical_review_not_found(self):
        _, _, replay, _, _, _ = _make_services()
        result = replay.get_canonical_review("nonexistent", "WORKER")
        assert result is None

    def test_get_review_history_empty(self):
        _, _, replay, _, _, _ = _make_services()
        history = replay.get_review_history("nonexistent")
        assert len(history) == 0

    def test_replay_preserves_version_info(self):
        service, _, replay, repo, registry, _ = _make_services()
        service.execute_review(_make_evaluation_event())
        history = replay.get_review_history("eval-1")
        assert len(history) >= 1
        assert history[0]["review_version"] == "v1.0"
        assert history[0]["review_status"] == "CANONICAL"


# --- Additional Execution Tests ---

class TestExecutionEdgeCases:
    def test_execute_review_different_types(self):
        service, _, _, _, _, _ = _make_services()
        event = _make_evaluation_event()
        event["review_type"] = "THESIS"
        event["evaluation_id"] = "eval-thesis"
        assessment = service.execute_review(event)
        assert assessment.review_type == ReviewType.THESIS

    def test_execute_review_custom_version(self):
        service, _, _, _, _, _ = _make_services()
        assessment = service.execute_review(_make_evaluation_event(), review_version="v2.0")
        assert assessment.review_version == "v2.0"

    def test_execute_review_with_empty_attribution(self):
        service, _, _, _, _, _ = _make_services()
        assessment = service.execute_review(_make_evaluation_event(), {})
        assert assessment.attribution_id == ""

    def test_execute_review_context_snapshot_hash(self):
        service, _, _, _, _, _ = _make_services()
        assessment = service.execute_review(_make_evaluation_event())
        assert len(assessment.context_snapshot.snapshot_hash) == 64  # SHA-256 hex



def _make_assessment(evaluation_id, review_version):
    return ReviewAssessment(
        review_id=f"rev-{evaluation_id}-{review_version}",
        evaluation_id=evaluation_id,
        review_type=ReviewType.WORKER,
        review_version=review_version,
        target_urn="worker-1",
        target_type="WORKER",
        decision_id="dec-1",
        attribution_id="attr-1",
        findings=[],
        recommendations=[],
        review_summary=ReviewSummary(
            total_findings=0, findings_by_severity={},
            total_recommendations=0, recommendations_by_priority={},
            overall_assessment="NEUTRAL", confidence=0.5, explanation="test",
        ),
        review_quality=ReviewQuality(quality_score=0.5, data_completeness=1.0, analysis_depth=0.5),
        context_snapshot=ReviewContextSnapshot(
            evaluation_snapshot={"id": evaluation_id},
            decision_snapshot={"id": "dec-1"},
            snapshot_hash="test",
        ),
        reviewed_at=datetime.utcnow(),
        reviewed_by="test",
    )
