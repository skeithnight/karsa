import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from typing import Dict, Any, List
from cryptography.hazmat.primitives.asymmetric import ed25519

from karsa.cio.exceptions import (
    ImmutabilityViolationException, QuorumNotMetException, DecisionNotFoundException,
    DuplicateJournalRefException, InvalidDecisionSignatureException
)
from karsa.cio.value_objects import (
    CommitteeVote, OverrideReason, SignaturePayload, PortfolioSnapshotReference
)
from karsa.cio.models import CIODecisionAggregate
from karsa.cio.projections import PortfolioStateProjection
from karsa.cio.ports import DecisionJournalPort, GovernanceExceptionPort, EventPublisherPort
from karsa.cio.repositories import InMemoryCIODecisionRepository
from karsa.cio.services import CIODecisionService, PortfolioOrchestrationService
from karsa.cio.api import router, get_decision_service, get_orchestration_service
import karsa.cio.api as api_module
from karsa.execution.domain.security import generate_key_pair, verify_payload_signature

# ----------------- Mock Ports -----------------

class MockDecisionJournalPort(DecisionJournalPort):
    def __init__(self, existing_journals: List[str]):
        self.existing_journals = existing_journals

    def verify_journal_exists(self, journal_ref: str) -> bool:
        return journal_ref in self.existing_journals

    def get_journal_expectations(self, journal_ref: str) -> Dict[str, Any]:
        return {"expected_return_bps": 150, "probability": 0.8}

class MockGovernanceExceptionPort(GovernanceExceptionPort):
    def __init__(self, valid_tokens: List[str]):
        self.valid_tokens = valid_tokens

    def verify_exception_token(self, exception_id: str, signature: str, payload: Dict[str, Any]) -> bool:
        return exception_id in self.valid_tokens

class MockEventPublisherPort(EventPublisherPort):
    def __init__(self):
        self.events = []

    def publish(self, event: Any) -> None:
        self.events.append(event)

# ----------------- Test Fixtures -----------------

@pytest.fixture
def crypto_keys():
    priv, pub = generate_key_pair()
    return priv, pub

@pytest.fixture
def service_setup(crypto_keys):
    priv, pub = crypto_keys
    repo = InMemoryCIODecisionRepository()
    journal_port = MockDecisionJournalPort(["urn:journal:dec-1", "urn:journal:dec-2"])
    gov_port = MockGovernanceExceptionPort(["exception-token-1"])
    publisher = MockEventPublisherPort()
    
    dec_service = CIODecisionService(repo, journal_port, gov_port, publisher, priv)
    orch_service = PortfolioOrchestrationService(repo)
    return dec_service, orch_service, repo, publisher, pub

# ----------------- Domain & Aggregate Tests -----------------

def test_aggregate_immutability():
    decision = CIODecisionAggregate(
        decision_id="dec-1",
        calculation_id="calc-1",
        governance_exception_id=None,
        decision_journal_ref="urn:journal:dec-1",
        portfolio_snapshot_hash="hash-123",
        action_type="APPROVE_ALLOCATION",
        target_node_type="PORTFOLIO",
        target_node_id="port-1",
        decision_payload={"allocated_weights": {"worker-1": 1.0}},
        cryptographic_signature="sig-xyz",
        created_at=datetime.utcnow(),
        votes=[CommitteeVote("voter-1", "APPROVE", datetime.utcnow())]
    )

    with pytest.raises(ImmutabilityViolationException):
        decision.action_type = "REJECT_ALLOCATION"

    with pytest.raises(ImmutabilityViolationException):
        del decision.cryptographic_signature

def test_value_object_validation():
    # Negative weight validation
    with pytest.raises(ValueError):
        SignaturePayload("dec-1", "port-1", {"w1": -0.5}, "hash-1")

    # Empty justification
    with pytest.raises(ValueError):
        OverrideReason("  ")

    # Invalid vote type
    with pytest.raises(ValueError):
        CommitteeVote("v1", "MAYBE", datetime.utcnow())

# ----------------- Service logic Tests -----------------

def test_create_decision_requires_valid_journal(service_setup):
    dec_svc, *_ = service_setup
    votes = [CommitteeVote("v1", "APPROVE", datetime.utcnow())]
    
    with pytest.raises(ValueError) as exc:
        dec_svc.create_decision(
            decision_id="dec-1",
            calculation_id="calc-1",
            governance_exception_id=None,
            decision_journal_ref="urn:journal:non-existent",
            portfolio_snapshot_hash="snapshot-1",
            action_type="APPROVE_ALLOCATION",
            target_node_type="PORTFOLIO",
            target_node_id="port-1",
            allocated_weights={"w1": 0.5},
            votes=votes
        )
    assert "does not exist" in str(exc.value)

def test_create_decision_enforces_quorum(service_setup):
    dec_svc, *_ = service_setup
    votes = [
        CommitteeVote("v1", "APPROVE", datetime.utcnow()),
        CommitteeVote("v2", "REJECT", datetime.utcnow())
    ]
    # approvals (1) is equal to rejections (1) -> should fail
    with pytest.raises(QuorumNotMetException):
        dec_svc.create_decision(
            decision_id="dec-1",
            calculation_id="calc-1",
            governance_exception_id=None,
            decision_journal_ref="urn:journal:dec-1",
            portfolio_snapshot_hash="snapshot-1",
            action_type="APPROVE_ALLOCATION",
            target_node_type="PORTFOLIO",
            target_node_id="port-1",
            allocated_weights={"w1": 0.5},
            votes=votes
        )

def test_create_decision_override_bypasses_quorum(service_setup):
    dec_svc, _, repo, *_ = service_setup
    
    # Overrides do not require votes, but require override reason justification
    with pytest.raises(ValueError):
        dec_svc.create_decision(
            decision_id="dec-1",
            calculation_id=None,
            governance_exception_id=None,
            decision_journal_ref="urn:journal:dec-1",
            portfolio_snapshot_hash="snapshot-1",
            action_type="OVERRIDE",
            target_node_type="PORTFOLIO",
            target_node_id="port-1",
            allocated_weights={"w1": 1.0},
            votes=[]
        )

    decision = dec_svc.create_decision(
        decision_id="dec-1",
        calculation_id=None,
        governance_exception_id=None,
        decision_journal_ref="urn:journal:dec-1",
        portfolio_snapshot_hash="snapshot-1",
        action_type="OVERRIDE",
        target_node_type="PORTFOLIO",
        target_node_id="port-1",
        allocated_weights={"w1": 1.0},
        votes=[],
        override_reason=OverrideReason("Manual override justifying risk allocation increase.")
    )
    assert decision.action_type == "OVERRIDE"

def test_signature_generation_and_payload_locking(service_setup):
    dec_svc, _, _, _, pub_key = service_setup
    votes = [CommitteeVote("v1", "APPROVE", datetime.utcnow())]

    decision = dec_svc.create_decision(
        decision_id="dec-1",
        calculation_id="calc-1",
        governance_exception_id="exception-token-1",
        decision_journal_ref="urn:journal:dec-1",
        portfolio_snapshot_hash="snapshot-123",
        action_type="APPROVE_ALLOCATION",
        target_node_type="PORTFOLIO",
        target_node_id="port-1",
        allocated_weights={"w1": 0.5},
        votes=votes
    )

    # Reconstruct payload and verify signature against public key
    serialized_payload = f"dec-1|port-1|w1:0.5|snapshot-123|exception-token-1"
    assert verify_payload_signature(pub_key, serialized_payload, decision.cryptographic_signature)

def test_duplicate_decision_journal_ref_rejected(service_setup):
    dec_svc, *_ = service_setup
    votes = [CommitteeVote("v1", "APPROVE", datetime.utcnow())]

    # Create first decision mapping to journal 1
    dec_svc.create_decision(
        decision_id="dec-1",
        calculation_id="calc-1",
        governance_exception_id=None,
        decision_journal_ref="urn:journal:dec-1",
        portfolio_snapshot_hash="snapshot-1",
        action_type="APPROVE_ALLOCATION",
        target_node_type="PORTFOLIO",
        target_node_id="port-1",
        allocated_weights={"w1": 0.5},
        votes=votes
    )

    # Creating second decision with same journal ref must fail
    with pytest.raises(DuplicateJournalRefException):
        dec_svc.create_decision(
            decision_id="dec-2",
            calculation_id="calc-2",
            governance_exception_id=None,
            decision_journal_ref="urn:journal:dec-1",
            portfolio_snapshot_hash="snapshot-1",
            action_type="APPROVE_ALLOCATION",
            target_node_type="PORTFOLIO",
            target_node_id="port-1",
            allocated_weights={"w1": 0.5},
            votes=votes
        )

# ----------------- API / Endpoint Tests -----------------

def test_api_endpoints(service_setup):
    dec_svc, orch_svc, *_ = service_setup
    from fastapi import FastAPI
    app = FastAPI()
    app.dependency_overrides[get_decision_service] = lambda: dec_svc
    app.dependency_overrides[get_orchestration_service] = lambda: orch_svc
    app.include_router(router)
    client = TestClient(app)

    # 1. Create Decision via API
    resp = client.post(
        "/cio/decisions",
        json={
            "decision_id": "dec-10",
            "calculation_id": "calc-10",
            "decision_journal_ref": "urn:journal:dec-2",
            "portfolio_snapshot_hash": "snapshot-10",
            "action_type": "APPROVE_ALLOCATION",
            "target_node_type": "PORTFOLIO",
            "target_node_id": "port-10",
            "allocated_weights": {"worker-1": 1.0},
            "votes": [{"voter_id": "v1", "vote_type": "APPROVE"}]
        }
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["decision_id"] == "dec-10"
    assert "signature" in data

    # 2. Get Decision via API
    resp = client.get("/cio/decisions/dec-10")
    assert resp.status_code == 200
    assert resp.json()["decision_journal_ref"] == "urn:journal:dec-2"

    # 3. Get Authorization signature state
    resp = client.get("/cio/decisions/dec-10/authorization")
    assert resp.status_code == 200
    assert resp.json()["portfolio_snapshot_hash"] == "snapshot-10"

    # 4. Get Committee Votes
    resp = client.get("/cio/decisions/dec-10/votes")
    assert resp.status_code == 200
    assert len(resp.json()["votes"]) == 1

    # 5. Create Portfolio state projection
    resp = client.post(
        "/cio/projections",
        json={
            "state_id": "state-10",
            "decision_id": "dec-10",
            "portfolio_tree": {"root": {"weights": {"worker-1": 1.0}}}
        }
    )
    assert resp.status_code == 201

    # 6. Fetch latest projection
    resp = client.get("/cio/projections/latest")
    assert resp.status_code == 200
    assert resp.json()["state_id"] == "state-10"
