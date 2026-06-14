import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from typing import Dict, Any, List

from karsa.post_mortem.exceptions import (
    AttributionWeightException,
    RecommendationStateConflictException,
    ImmutabilityViolationException,
)
from karsa.post_mortem.value_objects import (
    IncidentReference,
    FailureClassification,
    RootCauseContribution,
    PostMortemFinding,
    LessonLearned,
)
from karsa.post_mortem.models import PostMortemRecord, Recommendation
from karsa.post_mortem.ports import EventPublisherPort, SignatureValidationPort
from karsa.post_mortem.repositories import (
    InMemoryPostMortemRecordRepository,
    InMemoryRecommendationRepository,
)
from karsa.post_mortem.services import PostMortemService, RecommendationRegistryService
from karsa.post_mortem.api import router, configure_api
import karsa.post_mortem.api as api_module
from karsa.shared.infrastructure.uow import ConcurrencyConflictError
from fastapi import FastAPI, status

# ----------------- Mock Ports -----------------

class MockEventPublisherPort(EventPublisherPort):
    def __init__(self):
        self.events = []

    def publish(self, event: Any) -> None:
        self.events.append(event)

class MockSignatureValidationPort(SignatureValidationPort):
    def validate_signature(self, target_context: str, signature: str, payload: Dict[str, Any]) -> bool:
        # Only allow if the signature matches the target context's authorized signature name
        if target_context == "GOVERNANCE" and signature == "sig_gov_auth":
            return True
        if target_context == "ALLOCATION" and signature == "sig_alloc_auth":
            return True
        return False

# ----------------- Test Fixtures -----------------

@pytest.fixture
def service_setup():
    record_repo = InMemoryPostMortemRecordRepository()
    rec_repo = InMemoryRecommendationRepository()
    publisher = MockEventPublisherPort()
    sig_validator = MockSignatureValidationPort()
    
    pm_service = PostMortemService(record_repo, rec_repo, publisher)
    rec_service = RecommendationRegistryService(rec_repo, publisher, sig_validator)
    
    return pm_service, rec_service, record_repo, rec_repo, publisher

@pytest.fixture
def api_client(service_setup):
    pm_service, rec_service, _, _, _ = service_setup
    configure_api(pm_service, rec_service)
    
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)

# ----------------- Value Object & Aggregate Invariant Tests -----------------

def test_weights_sum_to_one():
    # Valid post-mortem record (weights sum to exactly 1.0)
    fc = FailureClassification("THESIS_FAILURE", "HIGH")
    rc1 = RootCauseContribution("PARAMETER_OVERFITTING", 0.6, "Overfitting on vol")
    rc2 = RootCauseContribution("RESEARCH_FAILURE", 0.4, "Stale signals")
    findings = PostMortemFinding(timeline_events=[], evidence_uris=[])
    
    record = PostMortemRecord(
        postmortem_id="pm-1",
        incident_ref=IncidentReference("urn:karsa:incident:thesis:123"),
        failure_classification=fc,
        root_causes=[rc1, rc2],
        findings=findings,
        created_at=datetime.utcnow()
    )
    assert record.postmortem_id == "pm-1"

def test_invalid_weight_rejected():
    fc = FailureClassification("THESIS_FAILURE", "HIGH")
    rc1 = RootCauseContribution("PARAMETER_OVERFITTING", 0.6, "Overfitting on vol")
    rc2 = RootCauseContribution("RESEARCH_FAILURE", 0.3, "Stale signals") # Sum is 0.9
    findings = PostMortemFinding(timeline_events=[], evidence_uris=[])
    
    with pytest.raises(AttributionWeightException):
        PostMortemRecord(
            postmortem_id="pm-1",
            incident_ref=IncidentReference("urn:karsa:incident:thesis:123"),
            failure_classification=fc,
            root_causes=[rc1, rc2],
            findings=findings,
            created_at=datetime.utcnow()
        )

def test_postmortem_record_immutable():
    fc = FailureClassification("THESIS_FAILURE", "HIGH")
    rc = RootCauseContribution("PARAMETER_OVERFITTING", 1.0, "Overfitting on vol")
    findings = PostMortemFinding(timeline_events=[], evidence_uris=[])
    
    record = PostMortemRecord(
        postmortem_id="pm-1",
        incident_ref=IncidentReference("urn:karsa:incident:thesis:123"),
        failure_classification=fc,
        root_causes=[rc],
        findings=findings,
        created_at=datetime.utcnow()
    )
    
    with pytest.raises(ImmutabilityViolationException):
        record.postmortem_id = "pm-new"

    with pytest.raises(ImmutabilityViolationException):
        del record.created_at

# ----------------- Recommendation Lifecycle State Transition Tests -----------------

def test_recommendation_accept():
    rec = Recommendation(
        recommendation_id="rec-1",
        postmortem_id="pm-1",
        target_context="GOVERNANCE",
        action_item="Reduce max leverage",
        parameters={"leverage": 1.5},
        state="PROPOSED",
        version=1,
        updated_at=datetime.utcnow()
    )
    rec.accept()
    assert rec.state == "ACCEPTED"
    assert rec.version == 2

def test_recommendation_reject():
    rec = Recommendation(
        recommendation_id="rec-1",
        postmortem_id="pm-1",
        target_context="GOVERNANCE",
        action_item="Reduce max leverage",
        parameters={"leverage": 1.5},
        state="PROPOSED",
        version=1,
        updated_at=datetime.utcnow()
    )
    rec.reject()
    assert rec.state == "REJECTED"
    assert rec.version == 2

def test_recommendation_implement():
    rec = Recommendation(
        recommendation_id="rec-1",
        postmortem_id="pm-1",
        target_context="GOVERNANCE",
        action_item="Reduce max leverage",
        parameters={"leverage": 1.5},
        state="PROPOSED",
        version=1,
        updated_at=datetime.utcnow()
    )
    rec.accept()
    rec.implement()
    assert rec.state == "IMPLEMENTED"
    assert rec.version == 3

def test_recommendation_expire():
    # Proposed -> Expired
    rec1 = Recommendation(
        recommendation_id="rec-1",
        postmortem_id="pm-1",
        target_context="GOVERNANCE",
        action_item="Reduce max leverage",
        parameters={"leverage": 1.5},
        state="PROPOSED",
        version=1,
        updated_at=datetime.utcnow()
    )
    rec1.expire()
    assert rec1.state == "EXPIRED"
    assert rec1.version == 2

    # Accepted -> Expired
    rec2 = Recommendation(
        recommendation_id="rec-2",
        postmortem_id="pm-1",
        target_context="GOVERNANCE",
        action_item="Reduce max leverage",
        parameters={"leverage": 1.5},
        state="PROPOSED",
        version=1,
        updated_at=datetime.utcnow()
    )
    rec2.accept()
    rec2.expire()
    assert rec2.state == "EXPIRED"
    assert rec2.version == 3

def test_invalid_transition_rejected_to_implemented():
    rec = Recommendation(
        recommendation_id="rec-1",
        postmortem_id="pm-1",
        target_context="GOVERNANCE",
        action_item="Reduce max leverage",
        parameters={"leverage": 1.5},
        state="PROPOSED",
        version=1,
        updated_at=datetime.utcnow()
    )
    rec.reject()
    with pytest.raises(RecommendationStateConflictException):
        rec.implement()

def test_invalid_transition_expired_to_accepted():
    rec = Recommendation(
        recommendation_id="rec-1",
        postmortem_id="pm-1",
        target_context="GOVERNANCE",
        action_item="Reduce max leverage",
        parameters={"leverage": 1.5},
        state="PROPOSED",
        version=1,
        updated_at=datetime.utcnow()
    )
    rec.expire()
    with pytest.raises(RecommendationStateConflictException):
        rec.accept()

# ----------------- Ownership Enforcement Tests -----------------

def test_postmortem_cannot_accept_recommendation(service_setup):
    pm_svc, rec_svc, record_repo, rec_repo, _ = service_setup
    
    # Setup record and recommendation
    fc = FailureClassification("THESIS_FAILURE", "HIGH")
    rc = RootCauseContribution("PARAMETER_OVERFITTING", 1.0, "Overfitting")
    pm_svc.create_post_mortem(
        postmortem_id="pm-1",
        incident_ref=IncidentReference("urn:karsa:incident:thesis:1"),
        failure_classification=fc,
        root_causes=[rc],
        findings=PostMortemFinding([], []),
        created_at=datetime.utcnow()
    )
    
    pm_svc.create_recommendation(
        recommendation_id="rec-1",
        postmortem_id="pm-1",
        target_context="GOVERNANCE",
        action_item="Reduce leverage",
        parameters={"leverage": 1.5}
    )

    # Acceptance requires target context (GOVERNANCE) signature.
    # An unauthorized signature (or post-mortem calling context) must fail.
    with pytest.raises(PermissionError):
        rec_svc.accept_recommendation("rec-1", signature="unauthorized_signature", caller_payload={})

def test_postmortem_cannot_implement_recommendation(service_setup):
    pm_svc, rec_svc, record_repo, rec_repo, _ = service_setup
    
    fc = FailureClassification("THESIS_FAILURE", "HIGH")
    rc = RootCauseContribution("PARAMETER_OVERFITTING", 1.0, "Overfitting")
    pm_svc.create_post_mortem(
        postmortem_id="pm-1",
        incident_ref=IncidentReference("urn:karsa:incident:thesis:2"),
        failure_classification=fc,
        root_causes=[rc],
        findings=PostMortemFinding([], []),
        created_at=datetime.utcnow()
    )
    
    pm_svc.create_recommendation(
        recommendation_id="rec-1",
        postmortem_id="pm-1",
        target_context="GOVERNANCE",
        action_item="Reduce leverage",
        parameters={"leverage": 1.5}
    )

    # Transition to accepted first (using valid signature)
    rec_svc.accept_recommendation("rec-1", signature="sig_gov_auth", caller_payload={})

    # Implement call with invalid signature/post-mortem signature must fail
    with pytest.raises(PermissionError):
        rec_svc.implement_recommendation("rec-1", signature="unauthorized_signature", caller_payload={})

# ----------------- Concurrency / OCC Race Tests -----------------

def test_recommendation_accept_race(service_setup):
    pm_svc, rec_svc, record_repo, rec_repo, _ = service_setup
    
    fc = FailureClassification("THESIS_FAILURE", "HIGH")
    rc = RootCauseContribution("PARAMETER_OVERFITTING", 1.0, "Overfitting")
    pm_svc.create_post_mortem(
        postmortem_id="pm-1",
        incident_ref=IncidentReference("urn:karsa:incident:thesis:3"),
        failure_classification=fc,
        root_causes=[rc],
        findings=PostMortemFinding([], []),
        created_at=datetime.utcnow()
    )
    
    pm_svc.create_recommendation(
        recommendation_id="rec-1",
        postmortem_id="pm-1",
        target_context="GOVERNANCE",
        action_item="Reduce leverage",
        parameters={"leverage": 1.5}
    )

    # Simulate two separate lookups of the same proposed recommendation
    rec_writer1 = rec_repo.get_recommendation_by_id("rec-1")
    rec_writer2 = rec_repo.get_recommendation_by_id("rec-1")

    # Writer 1 accepts
    rec_writer1.accept()
    rec_repo.save_recommendation(rec_writer1)

    # Writer 2 accepts from the stale state (version 1)
    rec_writer2.accept()
    with pytest.raises(ConcurrencyConflictError):
        rec_repo.save_recommendation(rec_writer2)

def test_recommendation_reject_race(service_setup):
    pm_svc, rec_svc, record_repo, rec_repo, _ = service_setup
    
    fc = FailureClassification("THESIS_FAILURE", "HIGH")
    rc = RootCauseContribution("PARAMETER_OVERFITTING", 1.0, "Overfitting")
    pm_svc.create_post_mortem(
        postmortem_id="pm-1",
        incident_ref=IncidentReference("urn:karsa:incident:thesis:4"),
        failure_classification=fc,
        root_causes=[rc],
        findings=PostMortemFinding([], []),
        created_at=datetime.utcnow()
    )
    
    pm_svc.create_recommendation(
        recommendation_id="rec-1",
        postmortem_id="pm-1",
        target_context="GOVERNANCE",
        action_item="Reduce leverage",
        parameters={"leverage": 1.5}
    )

    rec_writer1 = rec_repo.get_recommendation_by_id("rec-1")
    rec_writer2 = rec_repo.get_recommendation_by_id("rec-1")

    # Writer 1 rejects
    rec_writer1.reject()
    rec_repo.save_recommendation(rec_writer1)

    # Writer 2 rejects from stale state
    rec_writer2.reject()
    with pytest.raises(ConcurrencyConflictError):
        rec_repo.save_recommendation(rec_writer2)

def test_recommendation_accept_reject_race(service_setup):
    pm_svc, rec_svc, record_repo, rec_repo, _ = service_setup
    
    fc = FailureClassification("THESIS_FAILURE", "HIGH")
    rc = RootCauseContribution("PARAMETER_OVERFITTING", 1.0, "Overfitting")
    pm_svc.create_post_mortem(
        postmortem_id="pm-1",
        incident_ref=IncidentReference("urn:karsa:incident:thesis:5"),
        failure_classification=fc,
        root_causes=[rc],
        findings=PostMortemFinding([], []),
        created_at=datetime.utcnow()
    )
    
    pm_svc.create_recommendation(
        recommendation_id="rec-1",
        postmortem_id="pm-1",
        target_context="GOVERNANCE",
        action_item="Reduce leverage",
        parameters={"leverage": 1.5}
    )

    rec_writer1 = rec_repo.get_recommendation_by_id("rec-1")
    rec_writer2 = rec_repo.get_recommendation_by_id("rec-1")

    # Writer 1 accepts
    rec_writer1.accept()
    rec_repo.save_recommendation(rec_writer1)

    # Writer 2 rejects
    rec_writer2.reject()
    with pytest.raises(ConcurrencyConflictError):
        rec_repo.save_recommendation(rec_writer2)

def test_recommendation_accept_expire_race(service_setup):
    pm_svc, rec_svc, record_repo, rec_repo, _ = service_setup
    
    fc = FailureClassification("THESIS_FAILURE", "HIGH")
    rc = RootCauseContribution("PARAMETER_OVERFITTING", 1.0, "Overfitting")
    pm_svc.create_post_mortem(
        postmortem_id="pm-1",
        incident_ref=IncidentReference("urn:karsa:incident:thesis:6"),
        failure_classification=fc,
        root_causes=[rc],
        findings=PostMortemFinding([], []),
        created_at=datetime.utcnow()
    )
    
    pm_svc.create_recommendation(
        recommendation_id="rec-1",
        postmortem_id="pm-1",
        target_context="GOVERNANCE",
        action_item="Reduce leverage",
        parameters={"leverage": 1.5}
    )

    rec_writer1 = rec_repo.get_recommendation_by_id("rec-1")
    rec_writer2 = rec_repo.get_recommendation_by_id("rec-1")

    # Writer 1 accepts
    rec_writer1.accept()
    rec_repo.save_recommendation(rec_writer1)

    # Writer 2 expires
    rec_writer2.expire()
    with pytest.raises(ConcurrencyConflictError):
        rec_repo.save_recommendation(rec_writer2)

# ----------------- Replay Chain Reconstruction Test -----------------

def test_replay_chain_reconstruction(service_setup):
    pm_svc, rec_svc, record_repo, rec_repo, _ = service_setup
    
    # Replay chain trace setup:
    # Thesis ID -> Decision Journal ID -> CIO Decision ID -> Execution ID -> Portfolio Snapshot ID -> Performance Evaluation ID -> Review ID -> Post-Mortem ID -> Recommendation ID
    thesis_id = "thesis_id_999"
    decision_journal_id = "dec_journal_id_888"
    cio_decision_id = "cio_dec_777"
    execution_id = "exec_id_666"
    portfolio_snapshot_id = "port_snap_555"
    performance_evaluation_id = "perf_eval_444"
    review_id = "rev_id_333"
    postmortem_id = "pm_id_222"
    recommendation_id = "rec_id_111"

    # Store replay chain references as URNs in evidence URIs of Findings
    evidence_uris = [
        f"urn:karsa:thesis:{thesis_id}",
        f"urn:karsa:decision_journal:{decision_journal_id}",
        f"urn:karsa:cio:{cio_decision_id}",
        f"urn:karsa:execution:{execution_id}",
        f"urn:karsa:portfolio:{portfolio_snapshot_id}",
        f"urn:karsa:performance:{performance_evaluation_id}",
        f"urn:karsa:review:{review_id}"
    ]
    
    fc = FailureClassification("THESIS_FAILURE", "CRITICAL")
    rc = RootCauseContribution("THESIS_FAILURE", 1.0, "Flawed thesis expectations")
    findings = PostMortemFinding(
        timeline_events=[{"event": "Thesis failure detected", "time": "2026-06-14T00:00:00Z"}],
        evidence_uris=evidence_uris
    )

    pm_svc.create_post_mortem(
        postmortem_id=postmortem_id,
        incident_ref=IncidentReference("urn:karsa:incident:thesis:replay_001"),
        failure_classification=fc,
        root_causes=[rc],
        findings=findings,
        created_at=datetime.utcnow()
    )

    pm_svc.create_recommendation(
        recommendation_id=recommendation_id,
        postmortem_id=postmortem_id,
        target_context="GOVERNANCE",
        action_item="De-leverage strategy",
        parameters={}
    )

    # Reconstruct the causal replay chain backwards starting from Recommendation ID
    rec = rec_repo.get_recommendation_by_id(recommendation_id)
    assert rec is not None
    assert rec.postmortem_id == postmortem_id

    pm_record = record_repo.get_record_by_id(rec.postmortem_id)
    assert pm_record is not None
    
    # Retrieve the referenced traces from the evidence URIs list
    refs = pm_record.findings.evidence_uris
    
    # Map back to extract the IDs
    trace_map = {}
    for ref in refs:
        parts = ref.split(":")
        context = parts[2]
        ident = parts[3]
        trace_map[context] = ident

    assert trace_map["thesis"] == thesis_id
    assert trace_map["decision_journal"] == decision_journal_id
    assert trace_map["cio"] == cio_decision_id
    assert trace_map["execution"] == execution_id
    assert trace_map["portfolio"] == portfolio_snapshot_id
    assert trace_map["performance"] == performance_evaluation_id
    assert trace_map["review"] == review_id

# ----------------- API Endpoints Tests -----------------

def test_api_endpoints(api_client):
    # 1. Create Post Mortem
    post_payload = {
        "postmortem_id": "pm-api-1",
        "incident_ref": "urn:karsa:incident:performance:999",
        "failure_classification": {
            "failure_type": "PERFORMANCE_FAILURE",
            "severity": "CRITICAL",
            "taxonomy_version": 1
        },
        "root_causes": [
            {
                "cause_category": "PERFORMANCE_FAILURE",
                "weight": 1.0,
                "description": "Exceeded max drawdown"
            }
        ],
        "findings": {
            "timeline_events": [{"event": "downward spike", "timestamp": "2026-06-14T09:00:00"}],
            "evidence_uris": ["urn:evidence:scorecard:123"]
        }
    }
    
    res = api_client.post("/post-mortem/records", json=post_payload)
    assert res.status_code == status.HTTP_201_CREATED
    assert res.json()["postmortem_id"] == "pm-api-1"

    # Get Post Mortem
    res = api_client.get("/post-mortem/records/pm-api-1")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["incident_ref"] == "urn:karsa:incident:performance:999"

    # 2. Create Recommendation
    rec_payload = {
        "recommendation_id": "rec-api-1",
        "postmortem_id": "pm-api-1",
        "target_context": "GOVERNANCE",
        "action_item": "Lower risk parameters",
        "parameters": {"max_risk": 0.2}
    }
    res = api_client.post("/post-mortem/recommendations", json=rec_payload)
    assert res.status_code == status.HTTP_201_CREATED
    assert res.json()["state"] == "PROPOSED"

    # Get Recommendation
    res = api_client.get("/post-mortem/recommendations/rec-api-1")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["state"] == "PROPOSED"

    # 3. Accept Recommendation
    # Authorized signature for GOVERNANCE is "sig_gov_auth"
    res = api_client.post(
        "/post-mortem/recommendations/rec-api-1/accept",
        json={"signature": "sig_gov_auth", "caller_payload": {}}
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["state"] == "ACCEPTED"

    # 4. Implement Recommendation
    res = api_client.post(
        "/post-mortem/recommendations/rec-api-1/implement",
        json={"signature": "sig_gov_auth", "caller_payload": {}}
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["state"] == "IMPLEMENTED"

# ----------------- Additional Branch Coverage Tests -----------------

def test_value_object_validations():
    # IncidentReference validation checks
    with pytest.raises(ValueError, match="incident_ref cannot be empty"):
        IncidentReference("")
    with pytest.raises(ValueError, match="must match format URN"):
        IncidentReference("urn:invalid")
    with pytest.raises(ValueError, match="has invalid format"):
        IncidentReference("urn:karsa:incident:too_short")

    # FailureClassification validation checks
    with pytest.raises(ValueError, match="failure_type cannot be empty"):
        FailureClassification("", "HIGH")
    with pytest.raises(ValueError, match="severity cannot be empty"):
        FailureClassification("THESIS_FAILURE", "")

    # RootCauseContribution validation checks
    with pytest.raises(ValueError, match="cause_category cannot be empty"):
        RootCauseContribution("", 0.5, "desc")
    with pytest.raises(ValueError, match="Weight must be between"):
        RootCauseContribution("THESIS_FAILURE", -0.1, "desc")
    with pytest.raises(ValueError, match="Weight must be between"):
        RootCauseContribution("THESIS_FAILURE", 1.1, "desc")
    with pytest.raises(ValueError, match="description cannot be empty"):
        RootCauseContribution("THESIS_FAILURE", 0.5, "")

    # PostMortemFinding validation checks
    with pytest.raises(ValueError, match="timeline_events cannot be None"):
        PostMortemFinding(None, [])
    with pytest.raises(ValueError, match="evidence_uris cannot be None"):
        PostMortemFinding([], None)

    # LessonLearned validation checks
    with pytest.raises(ValueError, match="action_item cannot be empty"):
        LessonLearned("", "GOVERNANCE", {})
    with pytest.raises(ValueError, match="target_context cannot be empty"):
        LessonLearned("action", "", {})
    with pytest.raises(ValueError, match="parameters cannot be None"):
        LessonLearned("action", "GOVERNANCE", None)


def test_aggregate_constructor_validations():
    fc = FailureClassification("THESIS_FAILURE", "HIGH")
    rc = RootCauseContribution("THESIS_FAILURE", 1.0, "desc")
    findings = PostMortemFinding([], [])
    now = datetime.utcnow()

    # PostMortemRecord validation checks
    with pytest.raises(ValueError, match="postmortem_id cannot be empty"):
        PostMortemRecord("", IncidentReference("urn:karsa:incident:t:1"), fc, [rc], findings, now)
    with pytest.raises(ValueError, match="incident_ref must be an instance"):
        PostMortemRecord("pm-1", "invalid", fc, [rc], findings, now)
    with pytest.raises(ValueError, match="failure_classification must be an instance"):
        PostMortemRecord("pm-1", IncidentReference("urn:karsa:incident:t:1"), "invalid", [rc], findings, now)
    with pytest.raises(ValueError, match="root_causes must be a list"):
        PostMortemRecord("pm-1", IncidentReference("urn:karsa:incident:t:1"), fc, "invalid", findings, now)
    with pytest.raises(ValueError, match="root_causes must be a list of RootCauseContribution"):
        PostMortemRecord("pm-1", IncidentReference("urn:karsa:incident:t:1"), fc, ["invalid"], findings, now)
    with pytest.raises(ValueError, match="findings must be an instance"):
        PostMortemRecord("pm-1", IncidentReference("urn:karsa:incident:t:1"), fc, [rc], "invalid", now)
    with pytest.raises(ValueError, match="created_at must be an instance"):
        PostMortemRecord("pm-1", IncidentReference("urn:karsa:incident:t:1"), fc, [rc], findings, "invalid")

    # Recommendation validation checks
    with pytest.raises(ValueError, match="recommendation_id cannot be empty"):
        Recommendation("", "pm-1", "GOVERNANCE", "action", {}, "PROPOSED", 1, now)
    with pytest.raises(ValueError, match="postmortem_id cannot be empty"):
        Recommendation("rec-1", "", "GOVERNANCE", "action", {}, "PROPOSED", 1, now)
    with pytest.raises(ValueError, match="target_context cannot be empty"):
        Recommendation("rec-1", "pm-1", "", "action", {}, "PROPOSED", 1, now)
    with pytest.raises(ValueError, match="action_item cannot be empty"):
        Recommendation("rec-1", "pm-1", "GOVERNANCE", "", {}, "PROPOSED", 1, now)
    with pytest.raises(ValueError, match="parameters cannot be None"):
        Recommendation("rec-1", "pm-1", "GOVERNANCE", "action", None, "PROPOSED", 1, now)
    with pytest.raises(ValueError, match="Invalid recommendation state"):
        Recommendation("rec-1", "pm-1", "GOVERNANCE", "action", {}, "INVALID", 1, now)
    with pytest.raises(ValueError, match="version must be a positive integer"):
        Recommendation("rec-1", "pm-1", "GOVERNANCE", "action", {}, "PROPOSED", 0, now)
    with pytest.raises(ValueError, match="updated_at must be an instance"):
        Recommendation("rec-1", "pm-1", "GOVERNANCE", "action", {}, "PROPOSED", 1, "invalid")


def test_recommendation_summary_projection_validations():
    from karsa.post_mortem.projections import RecommendationSummaryProjection
    now = datetime.utcnow()
    with pytest.raises(ValueError, match="recommendation_id cannot be empty"):
        RecommendationSummaryProjection("", "pm-1", "GOVERNANCE", "PROPOSED", now)
    with pytest.raises(ValueError, match="postmortem_id cannot be empty"):
        RecommendationSummaryProjection("rec-1", "", "GOVERNANCE", "PROPOSED", now)
    with pytest.raises(ValueError, match="target_context cannot be empty"):
        RecommendationSummaryProjection("rec-1", "pm-1", "", "PROPOSED", now)
    with pytest.raises(ValueError, match="state cannot be empty"):
        RecommendationSummaryProjection("rec-1", "pm-1", "GOVERNANCE", "", now)


def test_ports_abstract_methods():
    # Cover the abstract base classes in ports.py
    class DummyPublisher(EventPublisherPort):
        pass
    class DummyValidator(SignatureValidationPort):
        pass

    with pytest.raises(TypeError):
        DummyPublisher()
    with pytest.raises(TypeError):
        DummyValidator()


def test_service_error_paths(service_setup):
    pm_svc, rec_svc, record_repo, rec_repo, _ = service_setup
    
    # Setup record first
    fc = FailureClassification("THESIS_FAILURE", "HIGH")
    rc = RootCauseContribution("THESIS_FAILURE", 1.0, "desc")
    findings = PostMortemFinding([], [])
    now = datetime.utcnow()
    pm_svc.create_post_mortem("pm-1", IncidentReference("urn:karsa:incident:t:1"), fc, [rc], findings, now)

    # Test duplicate incident_ref check in service
    with pytest.raises(ImmutabilityViolationException, match="already has a post-mortem record"):
        pm_svc.create_post_mortem("pm-2", IncidentReference("urn:karsa:incident:t:1"), fc, [rc], findings, now)

    # create_recommendation with non-existent postmortem_id
    with pytest.raises(ValueError, match="does not exist"):
        pm_svc.create_recommendation("rec-1", "non-existent-pm", "GOVERNANCE", "action", {})

    # Create recommendation for success cases
    pm_svc.create_recommendation("rec-1", "pm-1", "GOVERNANCE", "action", {})

    # Verify reject service method works
    rec_svc.reject_recommendation("rec-1", "sig_gov_auth", {})
    assert rec_repo.get_recommendation_by_id("rec-1").state == "REJECTED"

    # Create another recommendation
    pm_svc.create_recommendation("rec-2", "pm-1", "GOVERNANCE", "action", {})
    # Verify expire service method works
    rec_svc.expire_recommendation("rec-2")
    assert rec_repo.get_recommendation_by_id("rec-2").state == "EXPIRED"

    # accept, reject, implement, expire with non-existent recommendation_id
    with pytest.raises(ValueError, match="not found"):
        rec_svc.accept_recommendation("non-existent-rec", "sig", {})
    with pytest.raises(ValueError, match="not found"):
        rec_svc.reject_recommendation("non-existent-rec", "sig", {})
    with pytest.raises(ValueError, match="not found"):
        rec_svc.implement_recommendation("non-existent-rec", "sig", {})
    with pytest.raises(ValueError, match="not found"):
        rec_svc.expire_recommendation("non-existent-rec")


def test_repository_not_found_paths(service_setup):
    pm_svc, rec_svc, record_repo, rec_repo, _ = service_setup
    assert record_repo.get_record_by_id("non-existent") is None
    assert record_repo.get_record_by_incident_ref("non-existent") is None
    assert rec_repo.get_recommendation_by_id("non-existent") is None

    # Test duplicate postmortem_id overwrite check in repo
    fc = FailureClassification("THESIS_FAILURE", "HIGH")
    rc = RootCauseContribution("THESIS_FAILURE", 1.0, "desc")
    findings = PostMortemFinding([], [])
    now = datetime.utcnow()
    record = PostMortemRecord("pm-1", IncidentReference("urn:karsa:incident:t:1"), fc, [rc], findings, now)
    record_repo.save_record(record)
    with pytest.raises(ImmutabilityViolationException, match="Cannot overwrite"):
        record_repo.save_record(record)


def test_api_error_responses(api_client):
    # GET record non-existent
    res = api_client.get("/post-mortem/records/non-existent")
    assert res.status_code == status.HTTP_404_NOT_FOUND

    # GET recommendation non-existent
    res = api_client.get("/post-mortem/recommendations/non-existent")
    assert res.status_code == status.HTTP_404_NOT_FOUND

    # POST create recommendation for non-existent post mortem
    rec_payload = {
        "recommendation_id": "rec-api-err",
        "postmortem_id": "non-existent-pm",
        "target_context": "GOVERNANCE",
        "action_item": "Lower limit",
        "parameters": {}
    }
    res = api_client.post("/post-mortem/recommendations", json=rec_payload)
    assert res.status_code == status.HTTP_400_BAD_REQUEST

    # POST transition non-existent recommendation
    trans_payload = {"signature": "sig_gov_auth", "caller_payload": {}}
    res = api_client.post("/post-mortem/recommendations/non-existent/accept", json=trans_payload)
    assert res.status_code == status.HTTP_400_BAD_REQUEST

    res = api_client.post("/post-mortem/recommendations/non-existent/reject", json=trans_payload)
    assert res.status_code == status.HTTP_400_BAD_REQUEST

    res = api_client.post("/post-mortem/recommendations/non-existent/implement", json=trans_payload)
    assert res.status_code == status.HTTP_400_BAD_REQUEST

    res = api_client.post("/post-mortem/recommendations/non-existent/expire")
    assert res.status_code == status.HTTP_404_NOT_FOUND

    # Create valid PM and Recommendation for API error transition tests
    post_payload = {
        "postmortem_id": "pm-api-err-1",
        "incident_ref": "urn:karsa:incident:performance:888",
        "failure_classification": {
            "failure_type": "PERFORMANCE_FAILURE",
            "severity": "CRITICAL",
            "taxonomy_version": 1
        },
        "root_causes": [
            {
                "cause_category": "PERFORMANCE_FAILURE",
                "weight": 1.0,
                "description": "desc"
            }
        ],
        "findings": {
            "timeline_events": [],
            "evidence_uris": []
        }
    }
    api_client.post("/post-mortem/records", json=post_payload)

    # Test duplicate PM creation returns 409
    res = api_client.post("/post-mortem/records", json=post_payload)
    assert res.status_code == status.HTTP_409_CONFLICT

    rec_payload = {
        "recommendation_id": "rec-api-err-1",
        "postmortem_id": "pm-api-err-1",
        "target_context": "GOVERNANCE",
        "action_item": "action",
        "parameters": {}
    }
    api_client.post("/post-mortem/recommendations", json=rec_payload)

    # Test unauthorized signature returns 403 Forbidden
    res = api_client.post(
        "/post-mortem/recommendations/rec-api-err-1/accept",
        json={"signature": "unauthorized", "caller_payload": {}}
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # Test reject API works
    res = api_client.post(
        "/post-mortem/recommendations/rec-api-err-1/reject",
        json={"signature": "sig_gov_auth", "caller_payload": {}}
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["state"] == "REJECTED"

    # Test invalid transition on rejected returns 409 Conflict
    res = api_client.post(
        "/post-mortem/recommendations/rec-api-err-1/accept",
        json={"signature": "sig_gov_auth", "caller_payload": {}}
    )
    assert res.status_code == status.HTTP_409_CONFLICT

    # Create another recommendation for expire API test
    rec_payload_2 = {
        "recommendation_id": "rec-api-err-2",
        "postmortem_id": "pm-api-err-1",
        "target_context": "GOVERNANCE",
        "action_item": "action",
        "parameters": {}
    }
    api_client.post("/post-mortem/recommendations", json=rec_payload_2)

    # Test expire API works
    res = api_client.post("/post-mortem/recommendations/rec-api-err-2/expire")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["state"] == "EXPIRED"


