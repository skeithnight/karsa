import pytest
import uuid
from datetime import datetime, timezone
from typing import List

from karsa.review.domain.models import ReviewSession, ReviewRecord, PostMortemRecord
from karsa.review.domain.value_objects import (
    DecisionQualityAssessment,
    FailureClassification,
    SuccessClassification,
    ImprovementRecommendation,
    ReviewMethodologyManifest
)
from karsa.review.domain.events import (
    ReviewRecordRecordedEvent,
    FailureClassificationRecordedEvent,
    PostMortemFinalizedEvent
)
from karsa.review.infrastructure.repositories_batch2 import (
    InMemoryReviewSessionRepository,
    InMemoryReviewRecordRepository,
    InMemoryPostMortemRecordRepository
)
from karsa.review.application.services_batch3 import (
    ReviewRecordingService,
    ReviewReplayService,
    ConsensusSolver,
    PostMortemService,
    ReviewInvalidationService,
    MethodologyDriftException,
    ReplayIntegrityException,
    serialize_and_hash_inputs
)


# Helper constructors
def make_session(status="INITIATED", raw_input_hash=None):
    sess_id = str(uuid.uuid4())
    return ReviewSession(
        session_id=sess_id,
        session_urn=f"urn:karsa:review:session:{sess_id}",
        horizon_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        horizon_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
        raw_input_manifest_hash=raw_input_hash or "a" * 64,
        status=status
    )


def make_record(session_urn, decision_id="dec-1", worker_urn="urn:karsa:worker:w1", review_version=1):
    rec_id = str(uuid.uuid4())
    manifest = ReviewMethodologyManifest("urn:karsa:m:1", "b" * 64, "v1", "gpt-4")
    dq = DecisionQualityAssessment(0.8, 0.9, 0.1)
    return ReviewRecord(
        record_id=rec_id,
        record_urn=f"urn:karsa:review:record:{rec_id}",
        session_urn=session_urn,
        decision_id=decision_id,
        worker_urn=worker_urn,
        review_methodology_urn="urn:karsa:m:1",
        review_policy_hash="b" * 64,
        review_prompt_version="v1",
        reviewer_model_version="gpt-4",
        review_methodology_manifest_hash=manifest.compute_hash(),
        decision_quality=dq,
        reviewed_at=datetime.now(timezone.utc),
        review_version=review_version
    )


# 1. REVIEW RECORDING SERVICE TESTS
def test_record_review_success():
    session_repo = InMemoryReviewSessionRepository()
    record_repo = InMemoryReviewRecordRepository()
    events = []
    service = ReviewRecordingService(record_repo, session_repo, events)

    # Seed conducting session
    session = make_session(status="CONDUCTING")
    session_repo.save(session)

    dq = DecisionQualityAssessment(0.8, 0.9, 0.1)
    record_id = str(uuid.uuid4())
    record_urn = f"urn:karsa:review:record:{record_id}"
    manifest = ReviewMethodologyManifest("urn:karsa:m:1", "b" * 64, "v1", "gpt-4")
    m_hash = manifest.compute_hash()

    # Pass reviewed_at=None to cover services_batch3.py line 109 else branch
    rec = service.record_review(
        record_id=record_id,
        record_urn=record_urn,
        session_urn=session.session_urn,
        decision_id="dec-1",
        worker_urn="urn:karsa:worker:w1",
        review_methodology_urn="urn:karsa:m:1",
        review_policy_hash="b" * 64,
        review_prompt_version="v1",
        reviewer_model_version="gpt-4",
        review_methodology_manifest_hash=m_hash,
        decision_quality=dq,
        reviewed_at=None,
        review_version=1
    )

    assert rec.record_id == record_id
    assert rec.is_active is True
    assert len(events) == 1
    assert isinstance(events[0], ReviewRecordRecordedEvent)
    assert events[0].record_urn == record_urn


def test_record_review_supersedes_existing():
    session_repo = InMemoryReviewSessionRepository()
    record_repo = InMemoryReviewRecordRepository()
    service = ReviewRecordingService(record_repo, session_repo)

    session = make_session(status="CONDUCTING")
    session_repo.save(session)

    # First record for worker-1 on dec-1
    r1 = make_record(session.session_urn, decision_id="dec-1", worker_urn="urn:karsa:worker:w1", review_version=1)
    record_repo.save(r1)

    # Record second review
    manifest = ReviewMethodologyManifest("urn:karsa:m:1", "b" * 64, "v1", "gpt-4")
    dq = DecisionQualityAssessment(0.8, 0.9, 0.1)
    r2_id = str(uuid.uuid4())
    r2_urn = f"urn:karsa:review:record:{r2_id}"

    service.record_review(
        record_id=r2_id,
        record_urn=r2_urn,
        session_urn=session.session_urn,
        decision_id="dec-1",
        worker_urn="urn:karsa:worker:w1",
        review_methodology_urn="urn:karsa:m:1",
        review_policy_hash="b" * 64,
        review_prompt_version="v1",
        reviewer_model_version="gpt-4",
        review_methodology_manifest_hash=manifest.compute_hash(),
        decision_quality=dq,
        reviewed_at=datetime.now(timezone.utc),
        review_version=2
    )

    # Fetch r1 from repo and assert it is superseded
    r1_fetched = record_repo.find_by_id(r1.record_id)
    assert r1_fetched.is_active is False
    assert r1_fetched.superseded_by_version == 2


def test_record_review_session_validation_failures():
    session_repo = InMemoryReviewSessionRepository()
    record_repo = InMemoryReviewRecordRepository()
    service = ReviewRecordingService(record_repo, session_repo)

    dq = DecisionQualityAssessment(0.8, 0.9, 0.1)
    manifest = ReviewMethodologyManifest("urn:karsa:m:1", "b" * 64, "v1", "gpt-4")

    # Session not found
    with pytest.raises(ValueError, match="ReviewSession not found"):
        service.record_review(
            record_id=str(uuid.uuid4()),
            record_urn="urn:karsa:review:record:r1",
            session_urn="urn:karsa:review:session:non-existent",
            decision_id="dec-1",
            worker_urn="urn:karsa:worker:w1",
            review_methodology_urn="urn:karsa:m:1",
            review_policy_hash="b" * 64,
            review_prompt_version="v1",
            reviewer_model_version="gpt-4",
            review_methodology_manifest_hash=manifest.compute_hash(),
            decision_quality=dq,
            reviewed_at=datetime.now(timezone.utc)
        )

    # Session exists but is INITIATED (not CONDUCTING)
    session = make_session(status="INITIATED")
    session_repo.save(session)
    with pytest.raises(ValueError, match="is not in CONDUCTING status"):
        service.record_review(
            record_id=str(uuid.uuid4()),
            record_urn="urn:karsa:review:record:r1",
            session_urn=session.session_urn,
            decision_id="dec-1",
            worker_urn="urn:karsa:worker:w1",
            review_methodology_urn="urn:karsa:m:1",
            review_policy_hash="b" * 64,
            review_prompt_version="v1",
            reviewer_model_version="gpt-4",
            review_methodology_manifest_hash=manifest.compute_hash(),
            decision_quality=dq,
            reviewed_at=datetime.now(timezone.utc)
        )


def test_record_review_manifest_hash_mismatch():
    session_repo = InMemoryReviewSessionRepository()
    record_repo = InMemoryReviewRecordRepository()
    service = ReviewRecordingService(record_repo, session_repo)

    session = make_session(status="CONDUCTING")
    session_repo.save(session)
    dq = DecisionQualityAssessment(0.8, 0.9, 0.1)

    with pytest.raises(ValueError, match="Methodology manifest hash mismatch"):
        service.record_review(
            record_id=str(uuid.uuid4()),
            record_urn="urn:karsa:review:record:r1",
            session_urn=session.session_urn,
            decision_id="dec-1",
            worker_urn="urn:karsa:worker:w1",
            review_methodology_urn="urn:karsa:m:1",
            review_policy_hash="b" * 64,
            review_prompt_version="v1",
            reviewer_model_version="gpt-4",
            review_methodology_manifest_hash="wrong-manifest-hash-64-chars-long-but-incorrect-value-here",
            decision_quality=dq,
            reviewed_at=datetime.now(timezone.utc)
        )


# 2. REVIEW REPLAY SERVICE TESTS
def test_replay_verify_methodology_success_and_failure():
    session_repo = InMemoryReviewSessionRepository()
    record_repo = InMemoryReviewRecordRepository()
    service = ReviewReplayService(record_repo, session_repo)

    session = make_session(status="CONDUCTING")
    rec = make_record(session.session_urn)

    # Success case
    service.verify_methodology_manifest(rec)

    # Bypassing immutability via __dict__ direct assignment to simulate drift
    rec.__dict__["review_prompt_version"] = "v2"

    with pytest.raises(MethodologyDriftException):
        service.verify_methodology_manifest(rec)


def test_replay_verify_replay_integrity():
    session_repo = InMemoryReviewSessionRepository()
    record_repo = InMemoryReviewRecordRepository()
    service = ReviewReplayService(record_repo, session_repo)

    decision_journal = {"trade_id": "t1", "action": "BUY"}
    performance = {"realized_pnl": 1500.0}
    attribution = {"market_factor": 0.2}

    expected_hash = serialize_and_hash_inputs(decision_journal, performance, attribution)

    session = make_session(status="CONDUCTING", raw_input_hash=expected_hash)
    session_repo.save(session)

    # Success
    service.verify_replay_integrity(session.session_urn, decision_journal, performance, attribution)

    # Integrity Failure
    different_perf = {"realized_pnl": 9999.0}
    with pytest.raises(ReplayIntegrityException):
        service.verify_replay_integrity(session.session_urn, decision_journal, different_perf, attribution)

    # Session not found
    with pytest.raises(ValueError, match="ReviewSession not found"):
        service.verify_replay_integrity("urn:karsa:review:session:none", decision_journal, performance, attribution)


# 3. CONSENSUS SOLVER & POST-MORTEM SERVICE TESTS
def test_consensus_solver_logic():
    solver = ConsensusSolver()
    session = make_session(status="CONDUCTING")
    
    r1 = make_record(session.session_urn, worker_urn="urn:karsa:worker:w1")
    r2 = make_record(session.session_urn, worker_urn="urn:karsa:worker:w2")
    r3 = make_record(session.session_urn, worker_urn="urn:karsa:worker:w3")
    
    records = [r1, r2, r3]
    
    fc1 = FailureClassification(True, False, False, False, False)
    fc2 = FailureClassification(True, True, False, False, False)
    fc3 = FailureClassification(False, True, False, False, False)
    
    sc1 = SuccessClassification(True, False, True)
    sc2 = SuccessClassification(True, True, False)
    sc3 = SuccessClassification(False, False, False)
    
    # Add thesis_refinement_actions to cover lines 252-253
    rec1 = ImprovementRecommendation("THESIS_REVIEW_REQUIRED", "t", "HIGH", ["Action A"])
    rec2 = ImprovementRecommendation("EXECUTION_WARNING", "e", "MEDIUM", ["Action B"])
    rec3 = ImprovementRecommendation("THESIS_REVIEW_REQUIRED", "t", "HIGH", ["Action A", "Action C"])

    # Uniform weights:
    # thesis_error is True (2 vs 1) -> True
    # execution_error is True (2 vs 1) -> True
    # timing, sizing, calibration are False (0 vs 3) -> False
    # alpha_gen is True (2 vs 1) -> True
    # rec wins THESIS_REVIEW_REQUIRED
    fc, sc, rec = solver.solve_consensus(
        records=records,
        failure_classifications=[fc1, fc2, fc3],
        success_classifications=[sc1, sc2, sc3],
        recommendations=[rec1, rec2, rec3]
    )

    assert fc.thesis_error is True
    assert fc.execution_error is True
    assert sc.alpha_generation is True
    assert rec.recommendation_code == "THESIS_REVIEW_REQUIRED"
    assert "Action A" in rec.thesis_refinement_actions
    assert "Action C" in rec.thesis_refinement_actions

    # Weighted: w1=0.1, w2=0.1, w3=0.8
    # w3 asserts False on thesis_error -> weight sum for True is 0.2, False is 0.8 -> False wins!
    fc_w, _, rec_w = solver.solve_consensus(
        records=records,
        failure_classifications=[fc1, fc2, fc3],
        success_classifications=[sc1, sc2, sc3],
        recommendations=[rec1, rec2, rec3],
        reputation_weights={"urn:karsa:worker:w1": 0.1, "urn:karsa:worker:w2": 0.1, "urn:karsa:worker:w3": 0.8}
    )
    assert fc_w.thesis_error is False
    assert rec_w.recommendation_code == "THESIS_REVIEW_REQUIRED"  # still wins since rec3 is from w3


def test_consensus_solver_tie_breakers():
    solver = ConsensusSolver()
    session = make_session(status="CONDUCTING")
    
    r1 = make_record(session.session_urn, worker_urn="urn:karsa:worker:w1")
    r2 = make_record(session.session_urn, worker_urn="urn:karsa:worker:w2")
    records = [r1, r2]

    # Equal weights, different codes.
    # To cover line 244 (where winning_code is updated inside tie-breaker),
    # the first item processed (EXECUTION_WARNING, severity 2) must be weaker,
    # and the second item (THESIS_SUSPEND_RECOMMENDED, severity 5) must be stronger.
    rec1 = ImprovementRecommendation("EXECUTION_WARNING", "e", "MEDIUM")
    rec2 = ImprovementRecommendation("THESIS_SUSPEND_RECOMMENDED", "t", "CRITICAL")

    _, _, rec = solver.solve_consensus(
        records=records,
        failure_classifications=[
            FailureClassification(False, False, False, False, False),
            FailureClassification(False, False, False, False, False)
        ],
        success_classifications=[
            SuccessClassification(False, False, False),
            SuccessClassification(False, False, False)
        ],
        recommendations=[rec1, rec2]
    )
    assert rec.recommendation_code == "THESIS_SUSPEND_RECOMMENDED"


def test_consensus_solver_validation_errors():
    solver = ConsensusSolver()
    with pytest.raises(ValueError, match="No records provided"):
        solver.solve_consensus([], [], [], [])

    session = make_session(status="CONDUCTING")
    r = make_record(session.session_urn)
    with pytest.raises(ValueError, match="Mismatch in length"):
        solver.solve_consensus([r], [], [], [])


def test_finalize_postmortem_success():
    pm_repo = InMemoryPostMortemRecordRepository()
    record_repo = InMemoryReviewRecordRepository()
    solver = ConsensusSolver()
    events = []
    
    service = PostMortemService(pm_repo, record_repo, solver, events)

    session = make_session(status="CONDUCTING")
    
    r1 = make_record(session.session_urn, worker_urn="urn:karsa:worker:w1")
    r2 = make_record(session.session_urn, worker_urn="urn:karsa:worker:w2")
    record_repo.save(r1)
    record_repo.save(r2)

    fc1 = FailureClassification(True, False, False, False, False)
    fc2 = FailureClassification(True, False, False, False, False)
    sc1 = SuccessClassification(False, True, False)
    sc2 = SuccessClassification(False, True, False)
    rec1 = ImprovementRecommendation("EXECUTION_WARNING", "exec", "LOW")
    rec2 = ImprovementRecommendation("EXECUTION_WARNING", "exec", "LOW")

    pm_id = str(uuid.uuid4())
    pm_urn = f"urn:karsa:postmortem:record:{pm_id}"

    pm = service.finalize_postmortem(
        postmortem_id=pm_id,
        postmortem_urn=pm_urn,
        session_urn=session.session_urn,
        decision_id="dec-1",
        consensus_methodology_urn="urn:karsa:consensus:s1",
        consensus_policy_hash="c" * 64,
        input_review_record_urns=[r1.record_urn, r2.record_urn],
        failure_classifications=[fc1, fc2],
        success_classifications=[sc1, sc2],
        recommendations=[rec1, rec2]
    )

    assert pm.postmortem_id == pm_id
    assert pm.is_active is True
    assert len(events) == 2
    assert any(isinstance(e, PostMortemFinalizedEvent) for e in events)
    assert any(isinstance(e, FailureClassificationRecordedEvent) for e in events)

    # Test ValueError when review record not found (covers line 294)
    with pytest.raises(ValueError, match="ReviewRecord not found"):
        service.finalize_postmortem(
            postmortem_id=str(uuid.uuid4()),
            postmortem_urn="urn:karsa:postmortem:record:p2",
            session_urn=session.session_urn,
            decision_id="dec-1",
            consensus_methodology_urn="urn:karsa:consensus:s1",
            consensus_policy_hash="c" * 64,
            input_review_record_urns=["urn:karsa:review:record:non-existent"],
            failure_classifications=[fc1],
            success_classifications=[sc1],
            recommendations=[rec1]
        )


def test_finalize_postmortem_supersedes_existing():
    pm_repo = InMemoryPostMortemRecordRepository()
    record_repo = InMemoryReviewRecordRepository()
    solver = ConsensusSolver()
    service = PostMortemService(pm_repo, record_repo, solver)

    session = make_session(status="CONDUCTING")
    r = make_record(session.session_urn)
    record_repo.save(r)

    fc = FailureClassification(False, False, False, False, False)
    sc = SuccessClassification(False, False, False)
    rec = ImprovementRecommendation("EXECUTION_WARNING", "exec", "LOW")

    # Save initial active postmortem (will be superseded)
    pm1_id = str(uuid.uuid4())
    pm1_urn = f"urn:karsa:postmortem:record:{pm1_id}"
    pm1 = PostMortemRecord(
        postmortem_id=pm1_id,
        postmortem_urn=pm1_urn,
        session_urn=session.session_urn,
        decision_id="dec-1",
        consensus_methodology_urn="urn:karsa:consensus:s1",
        consensus_policy_hash="c" * 64,
        input_review_record_urns=[r.record_urn],
        failure_classification=fc,
        success_classification=sc,
        recommendation=rec,
        created_at=datetime.now(timezone.utc),
        is_active=True
    )
    pm_repo.save(pm1)

    # Save another postmortem for a different decision ID (will NOT be superseded, covers part of line 329)
    pm_diff_id = str(uuid.uuid4())
    pm_diff_urn = f"urn:karsa:postmortem:record:{pm_diff_id}"
    pm_diff = PostMortemRecord(
        postmortem_id=pm_diff_id,
        postmortem_urn=pm_diff_urn,
        session_urn=session.session_urn,
        decision_id="dec-different",
        consensus_methodology_urn="urn:karsa:consensus:s1",
        consensus_policy_hash="c" * 64,
        input_review_record_urns=[r.record_urn],
        failure_classification=fc,
        success_classification=sc,
        recommendation=rec,
        created_at=datetime.now(timezone.utc),
        is_active=True
    )
    pm_repo.save(pm_diff)

    # Save an inactive postmortem for dec-1 (will NOT be superseded, covers other part of line 329)
    pm_inactive_id = str(uuid.uuid4())
    pm_inactive_urn = f"urn:karsa:postmortem:record:{pm_inactive_id}"
    pm_inactive = PostMortemRecord(
        postmortem_id=pm_inactive_id,
        postmortem_urn=pm_inactive_urn,
        session_urn=session.session_urn,
        decision_id="dec-1",
        consensus_methodology_urn="urn:karsa:consensus:s1",
        consensus_policy_hash="c" * 64,
        input_review_record_urns=[r.record_urn],
        failure_classification=fc,
        success_classification=sc,
        recommendation=rec,
        created_at=datetime.now(timezone.utc),
        is_active=False
    )
    pm_repo.save(pm_inactive)

    # Finalize another postmortem for dec-1
    pm2_id = str(uuid.uuid4())
    pm2_urn = f"urn:karsa:postmortem:record:{pm2_id}"
    
    service.finalize_postmortem(
        postmortem_id=pm2_id,
        postmortem_urn=pm2_urn,
        session_urn=session.session_urn,
        decision_id="dec-1",
        consensus_methodology_urn="urn:karsa:consensus:s1",
        consensus_policy_hash="c" * 64,
        input_review_record_urns=[r.record_urn],
        failure_classifications=[fc],
        success_classifications=[sc],
        recommendations=[rec]
    )

    pm1_fetched = pm_repo.find_by_id(pm1_id)
    assert pm1_fetched.is_active is False
    assert pm1_fetched.superseded_by_version == 1

    pm_diff_fetched = pm_repo.find_by_id(pm_diff_id)
    assert pm_diff_fetched.is_active is True  # preserved

    pm_inactive_fetched = pm_repo.find_by_id(pm_inactive_id)
    assert pm_inactive_fetched.is_active is False
    assert pm_inactive_fetched.superseded_by_version is None  # unchanged


# 4. INVALIDATION FLOWS TESTS
def test_review_invalidation_chain():
    session_repo = InMemoryReviewSessionRepository()
    record_repo = InMemoryReviewRecordRepository()
    postmortem_repo = InMemoryPostMortemRecordRepository()
    service = ReviewInvalidationService(record_repo, postmortem_repo)

    session = make_session(status="CONDUCTING")
    
    # Chain of 2 records: r1 superseded by r2
    r1 = make_record(session.session_urn, review_version=1)
    r1.is_active = False
    r1.superseded_by_version = 2
    
    r2 = make_record(session.session_urn, decision_id=r1.decision_id, worker_urn=r1.worker_urn, review_version=2)
    r2.is_active = True
    
    record_repo.save(r1)
    record_repo.save(r2)

    # Invalidate chain starting at r1
    invalidated = service.invalidate_review_chain(r1.record_urn, invalidating_version=100)
    assert len(invalidated) == 1
    assert invalidated[0].record_urn == r2.record_urn
    assert invalidated[0].invalidated_by_version == 100
    assert invalidated[0].is_active is False


def test_postmortem_invalidation_chain():
    record_repo = InMemoryReviewRecordRepository()
    postmortem_repo = InMemoryPostMortemRecordRepository()
    service = ReviewInvalidationService(record_repo, postmortem_repo)

    session = make_session(status="CONDUCTING")
    fc = FailureClassification(False, False, False, False, False)
    sc = SuccessClassification(False, False, False)
    rec = ImprovementRecommendation("EXECUTION_WARNING", "exec", "LOW")

    pm1_id = str(uuid.uuid4())
    pm1 = PostMortemRecord(
        postmortem_id=pm1_id,
        postmortem_urn=f"urn:karsa:postmortem:record:{pm1_id}",
        session_urn=session.session_urn,
        decision_id="dec-1",
        consensus_methodology_urn="urn:karsa:consensus:s1",
        consensus_policy_hash="c" * 64,
        input_review_record_urns=["urn:karsa:review:record:r1"],
        failure_classification=fc,
        success_classification=sc,
        recommendation=rec,
        created_at=datetime.now(timezone.utc),
        postmortem_version=1,
        is_active=False,
        superseded_by_version=2
    )

    pm2_id = str(uuid.uuid4())
    pm2 = PostMortemRecord(
        postmortem_id=pm2_id,
        postmortem_urn=f"urn:karsa:postmortem:record:{pm2_id}",
        session_urn=session.session_urn,
        decision_id="dec-1",
        consensus_methodology_urn="urn:karsa:consensus:s1",
        consensus_policy_hash="c" * 64,
        input_review_record_urns=["urn:karsa:review:record:r1"],
        failure_classification=fc,
        success_classification=sc,
        recommendation=rec,
        created_at=datetime.now(timezone.utc),
        postmortem_version=2,
        is_active=True
    )

    postmortem_repo.save(pm1)
    postmortem_repo.save(pm2)

    invalidated = service.invalidate_postmortem_chain(pm1.postmortem_urn, invalidating_version=200)
    assert len(invalidated) == 1
    assert invalidated[0].postmortem_urn == pm2.postmortem_urn
    assert invalidated[0].invalidated_by_version == 200
    assert invalidated[0].is_active is False
