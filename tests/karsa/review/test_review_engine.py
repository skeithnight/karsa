import os
import json
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from typing import Any

from karsa.review import (
    ReviewSession,
    LearningFeedback,
    ReviewTarget,
    ReviewTargetType,
    ReviewSessionType,
    ReviewVerdictOutcome,
    LearningFeedbackCategory,
    EvidenceRetentionClass,
    ReviewEvidence,
    ReviewFinding,
    ReviewVerdict,
    LLMConfigSnapshot,
    InMemoryReviewSessionRepository,
    InMemoryLearningFeedbackRepository,
    FileReviewSessionRepository,
    FileLearningFeedbackRepository,
    ConcurrencyConflictError,
    ReviewService,
    LearningFeedbackService,
    ReviewVerdictReachedEvent,
    FeedbackAppliedEvent,
    ResearchRecommendationProposedEvent
)

# 1. Aggregate Lifecycle
def test_review_session_lifecycle():
    target = ReviewTarget(ReviewTargetType.WORKER, "worker-1", "v1")
    session = ReviewSession(
        session_id="sess-1",
        target=target,
        session_type=ReviewSessionType.AUTOMATED_ANOMALY,
        status="CREATED"
    )
    assert session.status == "CREATED"

    session.start_session()
    assert session.status == "IN_PROGRESS"

    finding = ReviewFinding("f-1", "BIAS", "HIGH", "Prompt deviation detected", datetime.utcnow())
    session.add_finding(finding)
    assert len(session.findings) == 1

    evidence = ReviewEvidence(
        evidence_id="ev-1",
        source_type="TRACE",
        source_reference_id="trace-123",
        evidence_hash="abc123hash",
        evidence_summary="summary text",
        retention_class=EvidenceRetentionClass.HOT,
        created_at=datetime.utcnow()
    )
    session.add_evidence(evidence)
    assert len(session.evidence) == 1

    verdict = ReviewVerdict("vrd-1", ReviewVerdictOutcome.PASS, "Model operates within boundaries", datetime.utcnow())
    session.complete_session(verdict)
    assert session.status == "COMPLETED"
    assert session.verdict == verdict


def test_learning_feedback_lifecycle():
    target = ReviewTarget(ReviewTargetType.THESIS_VERSION, "thesis-1", "v1.2")
    feedback = LearningFeedback(
        feedback_id="feed-1",
        session_id="sess-1",
        target=target,
        category=LearningFeedbackCategory.THESIS,
        suggested_action="INVALIDATE_VERSION",
        parameters={"invalidation_criteria": "sharpe_ratio"},
        status="PROPOSED"
    )
    assert feedback.status == "PROPOSED"

    feedback.accept()
    assert feedback.status == "ACCEPTED"

    now = datetime.utcnow()
    feedback.apply(now)
    assert feedback.status == "APPLIED"
    assert feedback.applied_at == now


# 2. Immutability
def test_review_session_immutability():
    target = ReviewTarget(ReviewTargetType.WORKER, "worker-1")
    session = ReviewSession(
        session_id="sess-1",
        target=target,
        session_type=ReviewSessionType.MANUAL_POST_MORTEM,
        status="CREATED"
    )
    session.start_session()
    
    # Can mutate in status IN_PROGRESS
    session.regime_id = "BULL"
    assert session.regime_id == "BULL"

    verdict = ReviewVerdict("vrd-1", ReviewVerdictOutcome.PASS, "justification", datetime.utcnow())
    session.complete_session(verdict)
    assert session.status == "COMPLETED"

    # Modification of finalized session must raise TypeError
    with pytest.raises(TypeError):
        session.regime_id = "BEAR"

    with pytest.raises(TypeError):
        session.status = "CREATED"


def test_learning_feedback_immutability():
    target = ReviewTarget(ReviewTargetType.WORKER, "worker-1")
    feedback = LearningFeedback(
        feedback_id="feed-1",
        session_id="sess-1",
        target=target,
        category=LearningFeedbackCategory.WORKER,
        suggested_action="SUSPEND_PROVIDER",
        parameters={},
        status="PROPOSED"
    )
    # Can mutate before finalization
    feedback.suggested_action = "DOWNGRADE_PRIORITY"
    assert feedback.suggested_action == "DOWNGRADE_PRIORITY"

    feedback.accept()
    feedback.apply(datetime.utcnow())
    assert feedback.status == "APPLIED"

    # Cannot modify parameters or suggested_action after finalization
    with pytest.raises(TypeError):
        feedback.suggested_action = "SUSPEND_PROVIDER"

    with pytest.raises(TypeError):
        feedback.parameters = {"new": "value"}


# 3. OCC Conflicts
def test_occ_conflict_detection():
    session_repo = InMemoryReviewSessionRepository()
    feedback_repo = InMemoryLearningFeedbackRepository()

    target = ReviewTarget(ReviewTargetType.WORKER, "worker-1")
    session_v1 = ReviewSession(
        session_id="sess-1",
        target=target,
        session_type=ReviewSessionType.AUTOMATED_ANOMALY,
        status="CREATED",
        aggregate_version=1
    )
    session_repo.save(session_v1)

    # Saving v1 again (conflict)
    session_conflict = ReviewSession(
        session_id="sess-1",
        target=target,
        session_type=ReviewSessionType.AUTOMATED_ANOMALY,
        status="CREATED",
        aggregate_version=1
    )
    with pytest.raises(ConcurrencyConflictError):
        session_repo.save(session_conflict)

    # Propose feedback
    feedback_v1 = LearningFeedback(
        feedback_id="feed-1",
        session_id="sess-1",
        target=target,
        category=LearningFeedbackCategory.WORKER,
        suggested_action="SUSPEND_PROVIDER",
        parameters={},
        status="PROPOSED",
        aggregate_version=1
    )
    feedback_repo.save(feedback_v1)

    feedback_conflict = LearningFeedback(
        feedback_id="feed-1",
        session_id="sess-1",
        target=target,
        category=LearningFeedbackCategory.WORKER,
        suggested_action="SUSPEND_PROVIDER",
        parameters={},
        status="PROPOSED",
        aggregate_version=1
    )
    with pytest.raises(ConcurrencyConflictError):
        feedback_repo.save(feedback_conflict)


# 4. Repository Persistence
def test_repository_persistence(tmp_path):
    session_dir = tmp_path / "sessions"
    feedback_dir = tmp_path / "feedback"
    
    session_repo = FileReviewSessionRepository(storage_dir=str(session_dir))
    feedback_repo = FileLearningFeedbackRepository(storage_dir=str(feedback_dir))

    target = ReviewTarget(ReviewTargetType.WORKER, "worker-1")
    session = ReviewSession(
        session_id="sess-1",
        target=target,
        session_type=ReviewSessionType.AUTOMATED_ANOMALY,
        status="CREATED",
        aggregate_version=1
    )
    session_repo.save(session)
    assert (session_dir / "sess-1.json").exists()

    retrieved = session_repo.find_by_id("sess-1")
    assert retrieved is not None
    assert retrieved.session_id == "sess-1"

    feedback = LearningFeedback(
        feedback_id="feed-1",
        session_id="sess-1",
        target=target,
        category=LearningFeedbackCategory.WORKER,
        suggested_action="SUSPEND_PROVIDER",
        parameters={},
        status="PROPOSED",
        aggregate_version=1
    )
    feedback_repo.save(feedback)
    assert (feedback_dir / "feed-1.json").exists()

    retrieved_feed = feedback_repo.find_by_id("feed-1")
    assert retrieved_feed is not None
    assert retrieved_feed.feedback_id == "feed-1"


# 5. Serialization/Deserialization
def test_serialization():
    target = ReviewTarget(ReviewTargetType.WORKER, "worker-1", "v2")
    config = LLMConfigSnapshot("gemini-pro", Decimal("0.0"), 42)
    evidence = ReviewEvidence(
        evidence_id="ev-1",
        source_type="TRACE",
        source_reference_id="trace-123",
        evidence_hash="hash",
        evidence_summary="summary",
        retention_class=EvidenceRetentionClass.WARM,
        created_at=datetime.utcnow(),
        llm_config=config
    )
    session = ReviewSession(
        session_id="sess-1",
        target=target,
        session_type=ReviewSessionType.AUTOMATED_ANOMALY,
        evidence=[evidence],
        status="CREATED",
        aggregate_version=1
    )
    d = session.to_dict()
    assert d["target"]["target_type"] == "WORKER"
    assert d["target"]["target_version"] == "v2"
    assert d["evidence"][0]["llm_config"]["model_name"] == "gemini-pro"
    assert d["evidence"][0]["llm_config"]["temperature"] == "0.0"

    deserialized = ReviewSession.from_dict(d)
    assert deserialized.target.target_type == ReviewTargetType.WORKER
    assert deserialized.evidence[0].llm_config.temperature == Decimal("0.0")


# 6. Replay Determinism
def test_replay_determinism():
    session_repo = InMemoryReviewSessionRepository()
    feedback_repo = InMemoryLearningFeedbackRepository()
    events = []
    
    feedback_service = LearningFeedbackService(feedback_repo, events)
    review_service = ReviewService(session_repo, feedback_service, events)

    # Ingest review audit events twice under separate setups
    session1 = review_service.start_review_session("WORKER", "worker-1", "AUTOMATED_ANOMALY")
    review_service.register_evidence(session1.session_id, "TRACE", "t-1", "summary text", "HOT")
    session1 = review_service.complete_review_session(session1.session_id, "CRITICAL_DEPRECATE", "out of bounds")

    # Reload from repository to fetch evidence list updates
    session1 = session_repo.find_by_id(session1.session_id)

    # Second setup: should output identical data states
    session_repo2 = InMemoryReviewSessionRepository()
    feedback_repo2 = InMemoryLearningFeedbackRepository()
    events2 = []
    feedback_service2 = LearningFeedbackService(feedback_repo2, events2)
    review_service2 = ReviewService(session_repo2, feedback_service2, events2)

    session2 = review_service2.start_review_session("WORKER", "worker-1", "AUTOMATED_ANOMALY")
    review_service2.register_evidence(session2.session_id, "TRACE", "t-1", "summary text", "HOT")
    session2 = review_service2.complete_review_session(session2.session_id, "CRITICAL_DEPRECATE", "out of bounds")
    
    session2 = session_repo2.find_by_id(session2.session_id)

    assert session1.status == session2.status
    assert len(session1.evidence) == len(session2.evidence)
    assert session1.evidence[0].evidence_hash == session2.evidence[0].evidence_hash


# 7. Event Emission
def test_event_emission():
    session_repo = InMemoryReviewSessionRepository()
    feedback_repo = InMemoryLearningFeedbackRepository()
    events = []
    
    feedback_service = LearningFeedbackService(feedback_repo, events)
    review_service = ReviewService(session_repo, feedback_service, events)

    session = review_service.start_review_session("WORKER", "worker-1", "AUTOMATED_ANOMALY")
    review_service.register_evidence(session.session_id, "TRACE", "trace-123", "summary context", "HOT")
    session = review_service.complete_review_session(session.session_id, "CRITICAL_DEPRECATE", "Failed test validation")

    # Should emit ReviewVerdictReachedEvent
    reached_ev = next(e for e in events if isinstance(e, ReviewVerdictReachedEvent))
    assert reached_ev.session_id == session.session_id
    assert reached_ev.outcome_rating == "CRITICAL_DEPRECATE"
    assert reached_ev.event_version == 1

    # Should auto propose feedback
    assert len(feedback_repo.list_all()) == 1


# 8. Feedback Lifecycle
def test_feedback_lifecycle_events():
    feedback_repo = InMemoryLearningFeedbackRepository()
    events = []
    service = LearningFeedbackService(feedback_repo, events)

    target = ReviewTarget(ReviewTargetType.THESIS_VERSION, "thesis-1")
    feedback = service.propose_feedback("sess-1", target, LearningFeedbackCategory.RESEARCH, "TRIGGER_RETRAINING", {"param": "value"})

    # Proposing research recommendation should emit event
    proposed_ev = next(e for e in events if isinstance(e, ResearchRecommendationProposedEvent))
    assert proposed_ev.feedback_id == feedback.feedback_id
    assert proposed_ev.action == "TRIGGER_RETRAINING"

    # Accept feedback
    service.accept_feedback(feedback.feedback_id)
    assert feedback_repo.find_by_id(feedback.feedback_id).status == "ACCEPTED"

    # Handle applied event
    applied_ev = FeedbackAppliedEvent(
        event_id="evt-applied",
        feedback_id=feedback.feedback_id,
        session_id="sess-1",
        target_type="THESIS_VERSION",
        target_id="thesis-1",
        target_version="",
        category="RESEARCH",
        suggested_action="TRIGGER_RETRAINING",
        applied_at=datetime.utcnow()
    )
    service.handle_feedback_applied(applied_ev)
    assert feedback_repo.find_by_id(feedback.feedback_id).status == "APPLIED"


# 9. Learning Loop Closure
def test_learning_loop_closure():
    session_repo = InMemoryReviewSessionRepository()
    feedback_repo = InMemoryLearningFeedbackRepository()
    events = []
    
    feedback_service = LearningFeedbackService(feedback_repo, events)
    review_service = ReviewService(session_repo, feedback_service, events)

    # 1. Start session
    session = review_service.start_review_session("THESIS_VERSION", "thesis-1", "AUTOMATED_ANOMALY", target_version="v1.0")
    assert session.status == "IN_PROGRESS"

    # 2. Register evidence (Summary stores hashes instead of duplication)
    review_service.register_evidence(session.session_id, "EVALUATION", "eval-1", "Quantitative sharpe deviation detected", "PERMANENT")
    
    # Reload session from repo
    session = session_repo.find_by_id(session.session_id)
    evidence = session.evidence[0]
    assert evidence.retention_class == EvidenceRetentionClass.PERMANENT
    assert evidence.evidence_hash == "6a22dcee02588285953c3cdd4b037372cf4bac723f61c2298e5a185af58873c1" # sha256 checksum

    # 3. Complete review with critical deprecate verdict
    session = review_service.complete_review_session(session.session_id, "CRITICAL_DEPRECATE", "Critical Sharpe ratio breach")
    assert session.status == "COMPLETED"

    # 4. LearningFeedback should be automatically proposed
    all_feeds = feedback_repo.list_all()
    assert len(all_feeds) == 1
    feedback = all_feeds[0]
    assert feedback.status == "PROPOSED"
    assert feedback.category == LearningFeedbackCategory.THESIS
    assert feedback.suggested_action == "INVALIDATE_VERSION"

    # 5. Process Applied event
    feedback_service.accept_feedback(feedback.feedback_id)
    applied_ev = FeedbackAppliedEvent(
        event_id="evt-9",
        feedback_id=feedback.feedback_id,
        session_id=session.session_id,
        target_type="THESIS_VERSION",
        target_id="thesis-1",
        target_version="v1.0",
        category="THESIS",
        suggested_action="INVALIDATE_VERSION",
        applied_at=datetime.utcnow()
    )
    feedback_service.handle_feedback_applied(applied_ev)
    assert feedback_repo.find_by_id(feedback.feedback_id).status == "APPLIED"


# 10. Evidence Hashing
def test_evidence_hashing():
    session_repo = InMemoryReviewSessionRepository()
    feedback_service = LearningFeedbackService(InMemoryLearningFeedbackRepository(), [])
    review_service = ReviewService(session_repo, feedback_service, [])

    session = review_service.start_review_session("WORKER", "worker-1", "AUTOMATED_ANOMALY")
    
    # Summary 1
    review_service.register_evidence(session.session_id, "TRACE", "t-1", "Test context A", "HOT")
    # Summary 2
    review_service.register_evidence(session.session_id, "TRACE", "t-2", "Test context B", "HOT")

    session = session_repo.find_by_id(session.session_id)
    assert session.evidence[0].evidence_hash != session.evidence[1].evidence_hash
    # SHA-256 for "Test context A"
    import hashlib
    expected = hashlib.sha256(b"Test context A").hexdigest()
    assert session.evidence[0].evidence_hash == expected


# 11. Retention Classification
def test_retention_classification():
    session_repo = InMemoryReviewSessionRepository()
    feedback_service = LearningFeedbackService(InMemoryLearningFeedbackRepository(), [])
    review_service = ReviewService(session_repo, feedback_service, [])

    session = review_service.start_review_session("WORKER", "worker-1", "AUTOMATED_ANOMALY")
    review_service.register_evidence(session.session_id, "TRACE", "t-1", "trace summaries", "COLD")

    session = session_repo.find_by_id(session.session_id)
    evidence = session.evidence[0]
    assert evidence.retention_class == EvidenceRetentionClass.COLD
