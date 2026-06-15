import pytest
import uuid
from datetime import datetime, timezone
from karsa.review.domain.models import (
    ReviewSession,
    ReviewRecord,
    PostMortemRecord,
    StateTransitionError,
    ImmutabilityViolationError
)
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
from karsa.review.domain.lineage import (
    reconstruct_review_lineage,
    reconstruct_postmortem_lineage
)

# 1. VALUE OBJECT TESTS

def test_decision_quality_assessment_full():
    # Valid
    dq = DecisionQualityAssessment(0.8, 0.9, 0.1)
    assert dq.outcome_independent_score == 0.8
    assert dq.outcome_dependent_score == 0.9
    assert dq.hindsight_bias_deviation == 0.1
    
    # Serialization
    d = dq.to_dict()
    assert d["outcome_independent_score"] == 0.8
    
    deser = DecisionQualityAssessment.from_dict(d)
    assert deser == dq
    
    # Boundary validation errors
    with pytest.raises(ValueError):
        DecisionQualityAssessment(-0.01, 0.5, 0.51)
    with pytest.raises(ValueError):
        DecisionQualityAssessment(1.01, 0.5, -0.51)
    with pytest.raises(ValueError):
        DecisionQualityAssessment(0.5, -0.1, -0.6)
    with pytest.raises(ValueError):
        DecisionQualityAssessment(0.5, 1.05, 0.55)
    with pytest.raises(ValueError):
        DecisionQualityAssessment(0.5, 0.8, 0.29)  # deviation mismatch


def test_failure_classification_full():
    fc = FailureClassification(True, False, True, False, True)
    assert fc.thesis_error is True
    
    d = fc.to_dict()
    deser = FailureClassification.from_dict(d)
    assert deser == fc
    
    with pytest.raises(ValueError):
        FailureClassification(1, False, False, False, False)


def test_success_classification_full():
    sc = SuccessClassification(True, False, True)
    assert sc.alpha_generation is True
    
    d = sc.to_dict()
    deser = SuccessClassification.from_dict(d)
    assert deser == sc
    
    with pytest.raises(ValueError):
        SuccessClassification(True, "False", True)


def test_improvement_recommendation_full():
    rec = ImprovementRecommendation("EXECUTION_WARNING", "exec_category", "MEDIUM", ["Action 1"])
    assert rec.recommendation_code == "EXECUTION_WARNING"
    
    d = rec.to_dict()
    deser = ImprovementRecommendation.from_dict(d)
    assert deser == rec
    
    with pytest.raises(ValueError):
        ImprovementRecommendation("BAD_CODE", "exec", "LOW")
    with pytest.raises(ValueError):
        ImprovementRecommendation("EXECUTION_WARNING", "exec", "BAD_SEVERITY")
    with pytest.raises(ValueError):
        ImprovementRecommendation("EXECUTION_WARNING", "", "MEDIUM")
    with pytest.raises(ValueError):
        ImprovementRecommendation("EXECUTION_WARNING", "exec", "MEDIUM", ["Action 1", 123])


def test_methodology_manifest_full():
    m = ReviewMethodologyManifest("urn:karsa:methodology:1", "hash" * 16, "v1", "gpt-4")
    d = m.to_dict()
    deser = ReviewMethodologyManifest.from_dict(d)
    assert deser == m
    
    # Compute Hash
    h = m.compute_hash()
    assert len(h) == 64
    
    # Validations
    with pytest.raises(ValueError):
        ReviewMethodologyManifest("", "hash" * 16, "v1", "gpt-4")
    with pytest.raises(ValueError):
        ReviewMethodologyManifest("urn:karsa:m:1", "", "v1", "gpt-4")
    with pytest.raises(ValueError):
        ReviewMethodologyManifest("urn:karsa:m:1", "hash" * 16, "", "gpt-4")
    with pytest.raises(ValueError):
        ReviewMethodologyManifest("urn:karsa:m:1", "hash" * 16, "v1", "")


# 2. AGGREGATE VALIDATION & LIFECYCLE TESTS

def test_review_session_validation_and_lifecycle():
    sess_id = str(uuid.uuid4())
    horizon_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    horizon_end = datetime(2026, 3, 31, tzinfo=timezone.utc)
    manifest_hash = "a" * 64
    
    # Invalid UUID
    with pytest.raises(ValueError):
        ReviewSession("invalid-uuid", f"urn:karsa:review:session:{sess_id}", horizon_start, horizon_end, manifest_hash)
        
    # Invalid URN prefix
    with pytest.raises(ValueError):
        ReviewSession(sess_id, f"urn:bad:prefix:{sess_id}", horizon_start, horizon_end, manifest_hash)
        
    # Invalid horizon order
    with pytest.raises(ValueError):
        ReviewSession(sess_id, f"urn:karsa:review:session:{sess_id}", horizon_end, horizon_start, manifest_hash)
        
    # Invalid status
    with pytest.raises(ValueError):
        ReviewSession(sess_id, f"urn:karsa:review:session:{sess_id}", horizon_start, horizon_end, manifest_hash, status="BAD_STATUS")
        
    # Valid construction and state transitions
    sess = ReviewSession(sess_id, f"urn:karsa:review:session:{sess_id}", horizon_start, horizon_end, manifest_hash)
    assert sess.status == "INITIATED"
    
    sess.start_reviews()
    assert sess.status == "CONDUCTING"
    
    sess.complete()
    assert sess.status == "COMPLETED"
    
    # Serialization
    sd = sess.to_dict()
    s_deser = ReviewSession.from_dict(sd)
    assert s_deser.session_id == sess.session_id
    assert s_deser.status == sess.status
    
    # Invalid transitions
    sess_new = ReviewSession(sess_id, f"urn:karsa:review:session:{sess_id}", horizon_start, horizon_end, manifest_hash)
    with pytest.raises(StateTransitionError):
        sess_new.complete()  # Cannot complete from INITIATED
        
    sess_new.start_reviews()
    with pytest.raises(StateTransitionError):
        sess_new.start_reviews()  # Cannot restart from CONDUCTING


def test_review_record_validation():
    rec_id = str(uuid.uuid4())
    sess_urn = f"urn:karsa:review:session:{str(uuid.uuid4())}"
    rec_urn = f"urn:karsa:review:record:{rec_id}"
    m = ReviewMethodologyManifest("urn:karsa:m:1", "b" * 64, "v1", "gpt-4")
    m_hash = m.compute_hash()
    dq = DecisionQualityAssessment(0.8, 0.9, 0.1)
    
    # Mismatched manifest hash
    with pytest.raises(ValueError):
        ReviewRecord(rec_id, rec_urn, sess_urn, "dec-1", "urn:karsa:worker:w1", "urn:karsa:m:1", "b" * 64, "v1", "gpt-4", "wrong-hash" * 8, dq, datetime.now(timezone.utc))

    # Invalid record_urn prefix
    with pytest.raises(ValueError):
        ReviewRecord(rec_id, f"urn:bad:prefix:{rec_id}", sess_urn, "dec-1", "urn:karsa:worker:w1", "urn:karsa:m:1", "b" * 64, "v1", "gpt-4", m_hash, dq, datetime.now(timezone.utc))

    # Invalid session_urn prefix
    with pytest.raises(ValueError):
        ReviewRecord(rec_id, rec_urn, "urn:bad:session:s1", "dec-1", "urn:karsa:worker:w1", "urn:karsa:m:1", "b" * 64, "v1", "gpt-4", m_hash, dq, datetime.now(timezone.utc))

    # Empty decision_id
    with pytest.raises(ValueError):
        ReviewRecord(rec_id, rec_urn, sess_urn, "", "urn:karsa:worker:w1", "urn:karsa:m:1", "b" * 64, "v1", "gpt-4", m_hash, dq, datetime.now(timezone.utc))

    # Invalid worker URN prefix
    with pytest.raises(ValueError):
        ReviewRecord(rec_id, rec_urn, sess_urn, "dec-1", "urn:bad:worker:w1", "urn:karsa:m:1", "b" * 64, "v1", "gpt-4", m_hash, dq, datetime.now(timezone.utc))

    # Invalid review_version
    with pytest.raises(ValueError):
        ReviewRecord(rec_id, rec_urn, sess_urn, "dec-1", "urn:karsa:worker:w1", "urn:karsa:m:1", "b" * 64, "v1", "gpt-4", m_hash, dq, datetime.now(timezone.utc), review_version=0)

    # Invalid superseded_by_version
    with pytest.raises(ValueError):
        ReviewRecord(rec_id, rec_urn, sess_urn, "dec-1", "urn:karsa:worker:w1", "urn:karsa:m:1", "b" * 64, "v1", "gpt-4", m_hash, dq, datetime.now(timezone.utc), superseded_by_version=0)

    # Invalid invalidated_by_version
    with pytest.raises(ValueError):
        ReviewRecord(rec_id, rec_urn, sess_urn, "dec-1", "urn:karsa:worker:w1", "urn:karsa:m:1", "b" * 64, "v1", "gpt-4", m_hash, dq, datetime.now(timezone.utc), invalidated_by_version=0)


def test_postmortem_record_validation():
    pm_id = str(uuid.uuid4())
    sess_urn = f"urn:karsa:review:session:{str(uuid.uuid4())}"
    pm_urn = f"urn:karsa:postmortem:record:{pm_id}"
    fc = FailureClassification(True, False, False, False, False)
    sc = SuccessClassification(False, True, False)
    rec = ImprovementRecommendation("EXECUTION_WARNING", "exec", "LOW")
    
    # Invalid postmortem URN prefix
    with pytest.raises(ValueError):
        PostMortemRecord(pm_id, "urn:bad:pm:record", sess_urn, "dec-1", "urn:karsa:consensus:s1", "c" * 64, ["urn:karsa:review:record:r1"], fc, sc, rec, datetime.now(timezone.utc))

    # Invalid session URN prefix
    with pytest.raises(ValueError):
        PostMortemRecord(pm_id, pm_urn, "urn:bad:session:s1", "dec-1", "urn:karsa:consensus:s1", "c" * 64, ["urn:karsa:review:record:r1"], fc, sc, rec, datetime.now(timezone.utc))

    # Empty decision_id
    with pytest.raises(ValueError):
        PostMortemRecord(pm_id, pm_urn, sess_urn, "", "urn:karsa:consensus:s1", "c" * 64, ["urn:karsa:review:record:r1"], fc, sc, rec, datetime.now(timezone.utc))

    # Invalid consensus methodology URN format
    with pytest.raises(ValueError):
        PostMortemRecord(pm_id, pm_urn, sess_urn, "dec-1", "urn:bad:consensus:s1", "c" * 64, ["urn:karsa:review:record:r1"], fc, sc, rec, datetime.now(timezone.utc))

    # Invalid consensus policy hash length
    with pytest.raises(ValueError):
        PostMortemRecord(pm_id, pm_urn, sess_urn, "dec-1", "urn:karsa:consensus:s1", "short-hash", ["urn:karsa:review:record:r1"], fc, sc, rec, datetime.now(timezone.utc))

    # Empty input review URNs
    with pytest.raises(ValueError):
        PostMortemRecord(pm_id, pm_urn, sess_urn, "dec-1", "urn:karsa:consensus:s1", "c" * 64, [], fc, sc, rec, datetime.now(timezone.utc))

    # Invalid input review URN format
    with pytest.raises(ValueError):
        PostMortemRecord(pm_id, pm_urn, sess_urn, "dec-1", "urn:karsa:consensus:s1", "c" * 64, ["urn:bad:review:record:1"], fc, sc, rec, datetime.now(timezone.utc))

    # Invalid versions
    with pytest.raises(ValueError):
        PostMortemRecord(pm_id, pm_urn, sess_urn, "dec-1", "urn:karsa:consensus:s1", "c" * 64, ["urn:karsa:review:record:r1"], fc, sc, rec, datetime.now(timezone.utc), postmortem_version=0)


# 3. IMMUTABILITY TESTS (ATTRIBUTES MUTATION & DELETION)

def test_review_session_immutability_and_deletion():
    sess_id = str(uuid.uuid4())
    horizon_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    horizon_end = datetime(2026, 3, 31, tzinfo=timezone.utc)
    manifest_hash = "a" * 64
    
    session = ReviewSession(
        session_id=sess_id,
        session_urn=f"urn:karsa:review:session:{sess_id}",
        horizon_start=horizon_start,
        horizon_end=horizon_end,
        raw_input_manifest_hash=manifest_hash
    )
    
    # Deleting attributes is allowed before finalization
    session.temp_attr = "temp"
    assert session.temp_attr == "temp"
    del session.temp_attr
    
    session.start_reviews()
    session.complete()
    
    # Cannot modify once completed
    with pytest.raises(ImmutabilityViolationError):
        session.horizon_start = datetime(2026, 1, 2, tzinfo=timezone.utc)
        
    # Cannot delete once completed
    with pytest.raises(ImmutabilityViolationError):
        del session.horizon_start


def test_review_record_immutability_and_deletion():
    rec_id = str(uuid.uuid4())
    sess_urn = f"urn:karsa:review:session:{str(uuid.uuid4())}"
    rec_urn = f"urn:karsa:review:record:{rec_id}"
    m = ReviewMethodologyManifest("urn:karsa:m:1", "b" * 64, "v1", "gpt-4")
    m_hash = m.compute_hash()
    dq = DecisionQualityAssessment(0.8, 0.9, 0.1)
    
    record = ReviewRecord(
        record_id=rec_id,
        record_urn=rec_urn,
        session_urn=sess_urn,
        decision_id="dec-1",
        worker_urn="urn:karsa:worker:w1",
        review_methodology_urn="urn:karsa:m:1",
        review_policy_hash="b" * 64,
        review_prompt_version="v1",
        reviewer_model_version="gpt-4",
        review_methodology_manifest_hash=m_hash,
        decision_quality=dq,
        reviewed_at=datetime.now(timezone.utc),
        review_version=1
    )
    
    # Try modifying core fields
    with pytest.raises(ImmutabilityViolationError):
        record.decision_id = "dec-2"
    with pytest.raises(ImmutabilityViolationError):
        record.reviewed_at = datetime.now(timezone.utc)
        
    # Try deleting core fields
    with pytest.raises(ImmutabilityViolationError):
        del record.decision_id
        
    # Allowed updates
    record.is_active = False
    record.superseded_by_version = 2
    record.invalidated_by_version = 3
    assert record.is_active is False
    assert record.superseded_by_version == 2
    assert record.invalidated_by_version == 3


def test_postmortem_record_immutability_and_deletion():
    pm_id = str(uuid.uuid4())
    sess_urn = f"urn:karsa:review:session:{str(uuid.uuid4())}"
    pm_urn = f"urn:karsa:postmortem:record:{pm_id}"
    fc = FailureClassification(True, False, False, False, False)
    sc = SuccessClassification(False, True, False)
    rec = ImprovementRecommendation("EXECUTION_WARNING", "exec", "LOW")
    
    pm = PostMortemRecord(
        postmortem_id=pm_id,
        postmortem_urn=pm_urn,
        session_urn=sess_urn,
        decision_id="dec-1",
        consensus_methodology_urn="urn:karsa:consensus:s1",
        consensus_policy_hash="c" * 64,
        input_review_record_urns=["urn:karsa:review:record:r1"],
        failure_classification=fc,
        success_classification=sc,
        recommendation=rec,
        created_at=datetime.now(timezone.utc),
        postmortem_version=1
    )
    
    # Try modifying
    with pytest.raises(ImmutabilityViolationError):
        pm.decision_id = "dec-2"
        
    # Try deleting
    with pytest.raises(ImmutabilityViolationError):
        del pm.decision_id
        
    # Allowed updates
    pm.is_active = False
    pm.superseded_by_version = 2
    pm.invalidated_by_version = 3
    assert pm.is_active is False


# 4. SUPERSEDE & INVALIDATE TESTS

def test_postmortem_record_supersede_and_invalidate():
    pm_id = str(uuid.uuid4())
    sess_urn = f"urn:karsa:review:session:{str(uuid.uuid4())}"
    pm_urn = f"urn:karsa:postmortem:record:{pm_id}"
    fc = FailureClassification(True, False, False, False, False)
    sc = SuccessClassification(False, True, False)
    rec = ImprovementRecommendation("EXECUTION_WARNING", "exec", "LOW")
    
    pm = PostMortemRecord(
        postmortem_id=pm_id,
        postmortem_urn=pm_urn,
        session_urn=sess_urn,
        decision_id="dec-1",
        consensus_methodology_urn="urn:karsa:consensus:s1",
        consensus_policy_hash="c" * 64,
        input_review_record_urns=["urn:karsa:review:record:r1"],
        failure_classification=fc,
        success_classification=sc,
        recommendation=rec,
        created_at=datetime.now(timezone.utc),
        postmortem_version=1
    )
    
    pm.supersede(next_version=2)
    assert pm.is_active is False
    assert pm.superseded_by_version == 2
    
    with pytest.raises(ImmutabilityViolationError):
        pm.invalidate(3)


def test_review_record_invalidate_active():
    rec_id = str(uuid.uuid4())
    sess_urn = f"urn:karsa:review:session:{str(uuid.uuid4())}"
    rec_urn = f"urn:karsa:review:record:{rec_id}"
    m = ReviewMethodologyManifest("urn:karsa:m:1", "b" * 64, "v1", "gpt-4")
    m_hash = m.compute_hash()
    dq = DecisionQualityAssessment(0.8, 0.9, 0.1)
    
    record = ReviewRecord(
        record_id=rec_id,
        record_urn=rec_urn,
        session_urn=sess_urn,
        decision_id="dec-1",
        worker_urn="urn:karsa:worker:w1",
        review_methodology_urn="urn:karsa:m:1",
        review_policy_hash="b" * 64,
        review_prompt_version="v1",
        reviewer_model_version="gpt-4",
        review_methodology_manifest_hash=m_hash,
        decision_quality=dq,
        reviewed_at=datetime.now(timezone.utc),
        review_version=1
    )
    
    record.invalidate(invalidating_version=5)
    assert record.is_active is False
    assert record.invalidated_by_version == 5


# 5. LINEAGE TRAVERSAL TESTS (LOOP & TERMINATION)

def test_lineage_empty_start_record():
    records = []
    assert reconstruct_review_lineage(records, "urn:karsa:review:record:r1") == []
    assert reconstruct_postmortem_lineage(records, "urn:karsa:postmortem:record:p1") == []


def test_lineage_loop_detection():
    sess_urn = f"urn:karsa:review:session:{str(uuid.uuid4())}"
    m_hash = ReviewMethodologyManifest("urn:karsa:m:1", "b" * 64, "v1", "gpt-4").compute_hash()
    dq = DecisionQualityAssessment(0.8, 0.9, 0.1)
    
    r1_id = str(uuid.uuid4())
    r1 = ReviewRecord(
        record_id=r1_id,
        record_urn=f"urn:karsa:review:record:{r1_id}",
        session_urn=sess_urn,
        decision_id="dec-1",
        worker_urn="urn:karsa:worker:w1",
        review_methodology_urn="urn:karsa:m:1",
        review_policy_hash="b" * 64,
        review_prompt_version="v1",
        reviewer_model_version="gpt-4",
        review_methodology_manifest_hash=m_hash,
        decision_quality=dq,
        reviewed_at=datetime.now(timezone.utc),
        review_version=1,
        is_active=False,
        superseded_by_version=2
    )

    r2_id = str(uuid.uuid4())
    r2 = ReviewRecord(
        record_id=r2_id,
        record_urn=f"urn:karsa:review:record:{r2_id}",
        session_urn=sess_urn,
        decision_id="dec-1",
        worker_urn="urn:karsa:worker:w1",
        review_methodology_urn="urn:karsa:m:1",
        review_policy_hash="b" * 64,
        review_prompt_version="v1",
        reviewer_model_version="gpt-4",
        review_methodology_manifest_hash=m_hash,
        decision_quality=dq,
        reviewed_at=datetime.now(timezone.utc),
        review_version=2,
        is_active=False,
        superseded_by_version=1  # Loop back to 1
    )
    
    lineage = reconstruct_review_lineage([r1, r2], r1.record_urn)
    assert len(lineage) == 2  # Walks to r2, then stops because r1 was already visited


# 6. EVENT VALIDATION & SERIALIZATION TESTS

def test_review_record_recorded_event_full():
    evt_id = str(uuid.uuid4())
    occurred_at = datetime.now(timezone.utc)
    
    event = ReviewRecordRecordedEvent(
        event_id=evt_id,
        correlation_id="corr-1",
        causation_id="caus-1",
        occurred_at=occurred_at,
        event_version=1,
        record_urn="urn:karsa:review:record:r1",
        session_urn="urn:karsa:review:session:s1",
        decision_id="dec-1",
        reviewer_urn="urn:karsa:worker:w1",
        review_methodology_manifest_hash="c" * 64,
        review_version=1
    )
    
    assert event.record_urn == "urn:karsa:review:record:r1"
    
    d = event.to_dict()
    deser = ReviewRecordRecordedEvent.from_dict(d)
    assert deser == event
    
    # DomainEvent superclass validation checks
    with pytest.raises(ValueError):
        # Invalid UUID event_id
        ReviewRecordRecordedEvent("bad-uuid", "corr-1", "caus-1", occurred_at, 1, "urn:karsa:review:record:r1", "urn:karsa:review:session:s1", "dec-1", "urn:karsa:worker:w1", "c" * 64, 1)
        
    with pytest.raises(ValueError):
        # Empty correlation_id
        ReviewRecordRecordedEvent(evt_id, "", "caus-1", occurred_at, 1, "urn:karsa:review:record:r1", "urn:karsa:review:session:s1", "dec-1", "urn:karsa:worker:w1", "c" * 64, 1)

    with pytest.raises(ValueError):
        # Empty causation_id
        ReviewRecordRecordedEvent(evt_id, "corr-1", "", occurred_at, 1, "urn:karsa:review:record:r1", "urn:karsa:review:session:s1", "dec-1", "urn:karsa:worker:w1", "c" * 64, 1)

    with pytest.raises(ValueError):
        # Invalid occurred_at type
        ReviewRecordRecordedEvent(evt_id, "corr-1", "caus-1", "not-a-datetime", 1, "urn:karsa:review:record:r1", "urn:karsa:review:session:s1", "dec-1", "urn:karsa:worker:w1", "c" * 64, 1)

    with pytest.raises(ValueError):
        # event_version < 1
        ReviewRecordRecordedEvent(evt_id, "corr-1", "caus-1", occurred_at, 0, "urn:karsa:review:record:r1", "urn:karsa:review:session:s1", "dec-1", "urn:karsa:worker:w1", "c" * 64, 1)

    # Subclass validation checks
    with pytest.raises(ValueError):
        # Invalid record_urn prefix
        ReviewRecordRecordedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "urn:bad:record:r1", "urn:karsa:review:session:s1", "dec-1", "urn:karsa:worker:w1", "c" * 64, 1)

    with pytest.raises(ValueError):
        # Invalid session_urn prefix
        ReviewRecordRecordedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "urn:karsa:review:record:r1", "urn:bad:session:s1", "dec-1", "urn:karsa:worker:w1", "c" * 64, 1)

    with pytest.raises(ValueError):
        # Empty decision_id
        ReviewRecordRecordedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "urn:karsa:review:record:r1", "urn:karsa:review:session:s1", "", "urn:karsa:worker:w1", "c" * 64, 1)

    with pytest.raises(ValueError):
        # Invalid reviewer_urn prefix
        ReviewRecordRecordedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "urn:karsa:review:record:r1", "urn:karsa:review:session:s1", "dec-1", "urn:bad:worker:w1", "c" * 64, 1)

    with pytest.raises(ValueError):
        # Invalid manifest hash format size
        ReviewRecordRecordedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "urn:karsa:review:record:r1", "urn:karsa:review:session:s1", "dec-1", "urn:karsa:worker:w1", "short", 1)

    with pytest.raises(ValueError):
        # Invalid version
        ReviewRecordRecordedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "urn:karsa:review:record:r1", "urn:karsa:review:session:s1", "dec-1", "urn:karsa:worker:w1", "c" * 64, 0)


def test_failure_classification_recorded_event_validation():
    evt_id = str(uuid.uuid4())
    occurred_at = datetime.now(timezone.utc)
    
    # Valid
    FailureClassificationRecordedEvent(
        event_id=evt_id,
        correlation_id="corr-1",
        causation_id="caus-1",
        occurred_at=occurred_at,
        event_version=1,
        decision_id="dec-1",
        thesis_error=True,
        execution_error=False,
        timing_error=False,
        sizing_error=False,
        calibration_error=False,
        recommendation_code="EXECUTION_WARNING",
        severity="LOW"
    )
    
    # Empty decision_id
    with pytest.raises(ValueError):
        FailureClassificationRecordedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "", True, False, False, False, False, "EXECUTION_WARNING", "LOW")

    # Non-boolean flags
    with pytest.raises(ValueError):
        FailureClassificationRecordedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "dec-1", "True", False, False, False, False, "EXECUTION_WARNING", "LOW")

    # Empty recommendation code
    with pytest.raises(ValueError):
        FailureClassificationRecordedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "dec-1", True, False, False, False, False, "", "LOW")

    # Empty severity
    with pytest.raises(ValueError):
        FailureClassificationRecordedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "dec-1", True, False, False, False, False, "EXECUTION_WARNING", "")


def test_postmortem_finalized_event_validation():
    evt_id = str(uuid.uuid4())
    occurred_at = datetime.now(timezone.utc)
    
    # Valid
    PostMortemFinalizedEvent(
        event_id=evt_id,
        correlation_id="corr-1",
        causation_id="caus-1",
        occurred_at=occurred_at,
        event_version=1,
        postmortem_urn="urn:karsa:postmortem:record:p1",
        session_urn="urn:karsa:review:session:s1",
        decision_id="dec-1",
        input_review_record_urns=["urn:karsa:review:record:r1"],
        postmortem_version=1,
        consensus_methodology_urn="urn:karsa:consensus:s1",
        consensus_policy_hash="c" * 64
    )
    
    # Invalid URN prefixes
    with pytest.raises(ValueError):
        PostMortemFinalizedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "urn:bad:pm:1", "urn:karsa:review:session:s1", "dec-1", ["urn:karsa:review:record:r1"], 1, "urn:karsa:consensus:s1", "c" * 64)

    with pytest.raises(ValueError):
        PostMortemFinalizedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "urn:karsa:postmortem:record:p1", "urn:bad:session:s1", "dec-1", ["urn:karsa:review:record:r1"], 1, "urn:karsa:consensus:s1", "c" * 64)

    # Empty input review records
    with pytest.raises(ValueError):
        PostMortemFinalizedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "urn:karsa:postmortem:record:p1", "urn:karsa:review:session:s1", "dec-1", [], 1, "urn:karsa:consensus:s1", "c" * 64)

    # Invalid input review URN format
    with pytest.raises(ValueError):
        PostMortemFinalizedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "urn:karsa:postmortem:record:p1", "urn:karsa:review:session:s1", "dec-1", ["urn:bad:record:r1"], 1, "urn:karsa:consensus:s1", "c" * 64)

    # Invalid postmortem_version
    with pytest.raises(ValueError):
        PostMortemFinalizedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "urn:karsa:postmortem:record:p1", "urn:karsa:review:session:s1", "dec-1", ["urn:karsa:review:record:r1"], 0, "urn:karsa:consensus:s1", "c" * 64)

    # Invalid consensus methodology URN format
    with pytest.raises(ValueError):
        PostMortemFinalizedEvent(evt_id, "corr-1", "caus-1", occurred_at, 1, "urn:karsa:postmortem:record:p1", "urn:karsa:review:session:s1", "dec-1", ["urn:karsa:review:record:r1"], 1, "urn:bad:consensus:s1", "c" * 64)


def test_postmortem_lineage_traversal():
    sess_urn = f"urn:karsa:review:session:{str(uuid.uuid4())}"
    fc = FailureClassification(True, False, False, False, False)
    sc = SuccessClassification(False, True, False)
    rec = ImprovementRecommendation("EXECUTION_WARNING", "exec", "LOW")
    
    pm1_id = str(uuid.uuid4())
    pm1 = PostMortemRecord(
        postmortem_id=pm1_id,
        postmortem_urn=f"urn:karsa:postmortem:record:{pm1_id}",
        session_urn=sess_urn,
        decision_id="dec-1",
        consensus_methodology_urn="urn:karsa:consensus:solver1",
        consensus_policy_hash="c" * 64,
        input_review_record_urns=["urn:karsa:review:record:1"],
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
        session_urn=sess_urn,
        decision_id="dec-1",
        consensus_methodology_urn="urn:karsa:consensus:solver1",
        consensus_policy_hash="c" * 64,
        input_review_record_urns=["urn:karsa:review:record:1", "urn:karsa:review:record:2"],
        failure_classification=fc,
        success_classification=sc,
        recommendation=rec,
        created_at=datetime.now(timezone.utc),
        postmortem_version=2,
        is_active=True
    )

    records = [pm1, pm2]
    lineage = reconstruct_postmortem_lineage(records, pm1.postmortem_urn)
    assert len(lineage) == 2
    assert lineage[0].postmortem_version == 1
    assert lineage[1].postmortem_version == 2


def test_other_events_serialization():
    evt_id1 = str(uuid.uuid4())
    occurred_at1 = datetime.now(timezone.utc)
    ev1 = FailureClassificationRecordedEvent(
        event_id=evt_id1,
        correlation_id="corr-1",
        causation_id="caus-1",
        occurred_at=occurred_at1,
        event_version=1,
        decision_id="dec-1",
        thesis_error=True,
        execution_error=False,
        timing_error=False,
        sizing_error=False,
        calibration_error=False,
        recommendation_code="EXECUTION_WARNING",
        severity="LOW"
    )
    d1 = ev1.to_dict()
    deser1 = FailureClassificationRecordedEvent.from_dict(d1)
    assert deser1.event_id == evt_id1
    assert deser1.thesis_error is True

    evt_id2 = str(uuid.uuid4())
    occurred_at2 = datetime.now(timezone.utc)
    ev2 = PostMortemFinalizedEvent(
        event_id=evt_id2,
        correlation_id="corr-2",
        causation_id="caus-2",
        occurred_at=occurred_at2,
        event_version=1,
        postmortem_urn="urn:karsa:postmortem:record:p1",
        session_urn="urn:karsa:review:session:s1",
        decision_id="dec-1",
        input_review_record_urns=["urn:karsa:review:record:r1"],
        postmortem_version=1,
        consensus_methodology_urn="urn:karsa:consensus:solver1",
        consensus_policy_hash="c" * 64
    )
    d2 = ev2.to_dict()
    deser2 = PostMortemFinalizedEvent.from_dict(d2)
    assert deser2.event_id == evt_id2
    assert deser2.input_review_record_urns == ["urn:karsa:review:record:r1"]


def test_aggregate_serialization():
    sess_id = str(uuid.uuid4())
    horizon_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    horizon_end = datetime(2026, 3, 31, tzinfo=timezone.utc)
    manifest_hash = "a" * 64
    session = ReviewSession(sess_id, f"urn:karsa:review:session:{sess_id}", horizon_start, horizon_end, manifest_hash)
    session_dict = session.to_dict()
    session_deser = ReviewSession.from_dict(session_dict)
    assert session_deser.session_id == session.session_id
    assert session_deser.horizon_start == session.horizon_start

    rec_id = str(uuid.uuid4())
    manifest = ReviewMethodologyManifest("urn:karsa:m:1", "b" * 64, "v1", "gpt-4")
    m_hash = manifest.compute_hash()
    dq = DecisionQualityAssessment(0.8, 0.9, 0.1)
    record = ReviewRecord(
        record_id=rec_id,
        record_urn=f"urn:karsa:review:record:{rec_id}",
        session_urn=f"urn:karsa:review:session:{sess_id}",
        decision_id="dec-1",
        worker_urn="urn:karsa:worker:w1",
        review_methodology_urn="urn:karsa:m:1",
        review_policy_hash="b" * 64,
        review_prompt_version="v1",
        reviewer_model_version="gpt-4",
        review_methodology_manifest_hash=m_hash,
        decision_quality=dq,
        reviewed_at=datetime.now(timezone.utc),
        review_version=1
    )
    record_dict = record.to_dict()
    record_deser = ReviewRecord.from_dict(record_dict)
    assert record_deser.record_id == record.record_id
    assert record_deser.reviewed_at == record.reviewed_at

    pm_id = str(uuid.uuid4())
    fc = FailureClassification(True, False, False, False, False)
    sc = SuccessClassification(False, True, False)
    rec = ImprovementRecommendation("EXECUTION_WARNING", "exec", "LOW")
    pm = PostMortemRecord(
        postmortem_id=pm_id,
        postmortem_urn=f"urn:karsa:postmortem:record:{pm_id}",
        session_urn=f"urn:karsa:review:session:{sess_id}",
        decision_id="dec-1",
        consensus_methodology_urn="urn:karsa:consensus:s1",
        consensus_policy_hash="c" * 64,
        input_review_record_urns=["urn:karsa:review:record:r1"],
        failure_classification=fc,
        success_classification=sc,
        recommendation=rec,
        created_at=datetime.now(timezone.utc),
        postmortem_version=1
    )
    pm_dict = pm.to_dict()
    pm_deser = PostMortemRecord.from_dict(pm_dict)
    assert pm_deser.postmortem_id == pm.postmortem_id
    assert pm_deser.created_at == pm.created_at


def test_postmortem_inactive_errors():
    sess_urn = f"urn:karsa:review:session:{str(uuid.uuid4())}"
    fc = FailureClassification(True, False, False, False, False)
    sc = SuccessClassification(False, True, False)
    rec = ImprovementRecommendation("EXECUTION_WARNING", "exec", "LOW")
    pm = PostMortemRecord(
        postmortem_id=str(uuid.uuid4()),
        postmortem_urn=f"urn:karsa:postmortem:record:{str(uuid.uuid4())}",
        session_urn=sess_urn,
        decision_id="dec-1",
        consensus_methodology_urn="urn:karsa:consensus:solver1",
        consensus_policy_hash="c" * 64,
        input_review_record_urns=["urn:karsa:review:record:1"],
        failure_classification=fc,
        success_classification=sc,
        recommendation=rec,
        created_at=datetime.now(timezone.utc),
        postmortem_version=1,
        is_active=False
    )
    with pytest.raises(ImmutabilityViolationError):
        pm.supersede(2)
    with pytest.raises(ImmutabilityViolationError):
        pm.invalidate(2)


def test_deleting_attributes_on_record_and_completed_session():
    sess_id = str(uuid.uuid4())
    horizon_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    horizon_end = datetime(2026, 3, 31, tzinfo=timezone.utc)
    manifest_hash = "a" * 64
    session = ReviewSession(sess_id, f"urn:karsa:review:session:{sess_id}", horizon_start, horizon_end, manifest_hash)
    session.start_reviews()
    session.complete()
    with pytest.raises(ImmutabilityViolationError):
        del session.horizon_start
        
    rec_id = str(uuid.uuid4())
    manifest = ReviewMethodologyManifest("urn:karsa:m:1", "b" * 64, "v1", "gpt-4")
    dq = DecisionQualityAssessment(0.8, 0.9, 0.1)
    record = ReviewRecord(
        record_id=rec_id,
        record_urn=f"urn:karsa:review:record:{rec_id}",
        session_urn=f"urn:karsa:review:session:{sess_id}",
        decision_id="dec-1",
        worker_urn="urn:karsa:worker:w1",
        review_methodology_urn="urn:karsa:m:1",
        review_policy_hash="b" * 64,
        review_prompt_version="v1",
        reviewer_model_version="gpt-4",
        review_methodology_manifest_hash=manifest.compute_hash(),
        decision_quality=dq,
        reviewed_at=datetime.now(timezone.utc),
        review_version=1
    )
    with pytest.raises(ImmutabilityViolationError):
        del record.decision_id

