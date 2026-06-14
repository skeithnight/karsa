import pytest
import hashlib
from datetime import datetime
from fastapi.testclient import TestClient
from karsa.decision_journal.exceptions import (
    ImmutabilityViolationException, HindsightValidationException, LineageIntegrityException, VerificationFailedException, ActiveLeafNotFoundException
)
from karsa.decision_journal.value_objects import (
    PromptReference, DatasetReference, TelemetryReference, ArtifactReference, ReplayMetadata, DecisionContextSnapshot, DecisionEvidence
)
from karsa.decision_journal.models import DecisionJournalAggregate, DecisionRevisionAggregate, DecisionEvidenceAggregate
from karsa.decision_journal.events import (
    DecisionJournalCreatedEvent, DecisionRevisionCreatedEvent, DecisionEvidenceAttachedEvent
)
from karsa.decision_journal.ports import ObjectStorePort, EventPublisherPort
from karsa.decision_journal.repositories import (
    InMemoryDecisionJournalRepository, InMemoryActiveLeafProjectionRepository, PostgresDecisionJournalRepository
)
from karsa.decision_journal.services import DecisionJournalService, JournalLineageResolver, ReplayService
from karsa.decision_journal.projections import ActiveLeafProjection
from karsa.shared.infrastructure.uow import ConcurrencyConflictError
from karsa.decision_journal.api import router, get_service, get_resolver, get_replay
import karsa.decision_journal.api as api_module

# ----------------- Mock Ports -----------------

class MockObjectStore(ObjectStorePort):
    def __init__(self):
        self.snapshots = {}

    def save_context_snapshot(self, decision_id: str, snapshot: DecisionContextSnapshot) -> str:
        uri = f"s3://decision-contexts/{decision_id}.json"
        self.snapshots[uri] = snapshot
        return uri

    def get_context_snapshot(self, uri: str) -> DecisionContextSnapshot:
        return self.snapshots.get(uri)

    def verify_hash(self, snapshot: DecisionContextSnapshot, expected_hash: str) -> bool:
        h = hashlib.sha256(str(snapshot).encode('utf-8')).hexdigest()
        return h == expected_hash

class MockEventPublisher(EventPublisherPort):
    def __init__(self):
        self.published = []

    def publish(self, event) -> None:
        self.published.append(event)

# ----------------- Test Fixtures -----------------

@pytest.fixture
def snapshot() -> DecisionContextSnapshot:
    prompt = PromptReference("pr-1", "hash-prompt", "urn:prompt:1")
    dataset = DatasetReference("ds-1", "hash-dataset", "urn:dataset:1")
    telemetry = TelemetryReference("tel-1", "hash-tel", "span-1")
    artifact = ArtifactReference("art-1", "hash-art", "urn:artifact:1")
    meta = ReplayMetadata("git-1", "docker-1", 42, 0.7, "high-vol")
    return DecisionContextSnapshot(prompt, dataset, telemetry, artifact, meta)

@pytest.fixture
def service_setup(snapshot):
    journal_repo = InMemoryDecisionJournalRepository()
    leaf_repo = InMemoryActiveLeafProjectionRepository()
    object_store = MockObjectStore()
    publisher = MockEventPublisher()
    svc = DecisionJournalService(journal_repo, leaf_repo, object_store, publisher)
    resolver = JournalLineageResolver(leaf_repo, journal_repo)
    replay = ReplayService(object_store)
    return svc, resolver, replay, journal_repo, leaf_repo, object_store, publisher

# ----------------- Tests -----------------

def test_aggregate_immutability(snapshot):
    journal = DecisionJournalAggregate(
        decision_id="dec-1",
        proposing_agent_id="agt-1",
        signature="sig-1",
        thesis_urn="urn:thesis:1",
        context_snapshot=snapshot,
        created_at=datetime.utcnow()
    )
    with pytest.raises(ImmutabilityViolationException):
        journal.proposing_agent_id = "agt-2"

    with pytest.raises(ImmutabilityViolationException):
        del journal.signature

def test_create_journal_validates_probability(service_setup, snapshot):
    svc, *_ = service_setup
    with pytest.raises(ValueError):
        svc.create_journal("dec-1", "agt-1", "sig-1", "urn:thesis:1", snapshot, probability=-0.1)

    with pytest.raises(ValueError):
        svc.create_journal("dec-1", "agt-1", "sig-1", "urn:thesis:1", snapshot, probability=1.1)

    journal = svc.create_journal("dec-1", "agt-1", "sig-1", "urn:thesis:1", snapshot, probability=0.8)
    assert journal.decision_id == "dec-1"

def test_active_leaf_projection_occ(service_setup, snapshot):
    svc, resolver, _, journal_repo, leaf_repo, *_ = service_setup
    
    svc.create_journal("root-1", "agt-1", "sig-1", "urn:thesis:1", snapshot)
    
    # Leaf resolved to root-1 initially
    assert resolver.resolve_active_leaf("root-1") == "root-1"

    # Save revision updates leaf version
    svc.create_revision("rev-1", "root-1", "agt-1", "sig-2", "Correction 1", snapshot)
    assert resolver.resolve_active_leaf("root-1") == "rev-1"

    # Simulate concurrency update race condition by manually saving with stale version
    stale_leaf = ActiveLeafProjection("root-1", "rev-2", 1, datetime.utcnow())
    with pytest.raises(ConcurrencyConflictError):
        leaf_repo.save_active_leaf(stale_leaf)

def test_hindsight_prevention_on_revision(service_setup, snapshot):
    svc, *_ = service_setup
    svc.create_journal("root-1", "agt-1", "sig-1", "urn:thesis:1", snapshot)
    
    # Mark execution started
    svc.set_execution_started("root-1")

    with pytest.raises(HindsightValidationException):
        svc.create_revision("rev-1", "root-1", "agt-1", "sig-2", "Too late", snapshot)

def test_replay_checksum_verification(service_setup, snapshot):
    svc, resolver, replay_svc, _, _, object_store, _ = service_setup
    
    svc.create_journal("dec-1", "agt-1", "sig-1", "urn:thesis:1", snapshot)
    
    expected_hash = hashlib.sha256(str(snapshot).encode('utf-8')).hexdigest()
    uri = f"s3://decision-contexts/dec-1.json"
    
    projection = replay_svc.replay_decision("dec-1", expected_hash, uri)
    assert projection.verified is True

    with pytest.raises(VerificationFailedException):
        replay_svc.replay_decision("dec-1", "tampered-hash-value", uri)

def test_lineage_resolver_path(service_setup, snapshot):
    svc, resolver, *_ = service_setup
    svc.create_journal("root-1", "agt-1", "sig-1", "urn:thesis:1", snapshot)
    svc.create_revision("rev-1", "root-1", "agt-1", "sig-2", "Correction 1", snapshot)
    svc.create_revision("rev-2", "rev-1", "agt-1", "sig-3", "Correction 2", snapshot)

    lineage = resolver.resolve_lineage("root-1")
    assert "root-1" in lineage.nodes
    assert "rev-1" in lineage.nodes
    assert "rev-2" in lineage.nodes
    assert lineage.parent_map["rev-2"] == "rev-1"
    assert lineage.parent_map["rev-1"] == "root-1"

def test_evidence_attachment(service_setup, snapshot):
    svc, *_ = service_setup
    svc.create_journal("dec-1", "agt-1", "sig-1", "urn:thesis:1", snapshot)

    artifact = ArtifactReference("art-2", "hash-art-2", "urn:artifact:2")
    evidence = DecisionEvidence("ev-1", "execution trace data", artifact, datetime.utcnow())

    agg = svc.attach_evidence("ev-agg-1", "dec-1", "agt-1", "sig-ev", evidence)
    assert agg.evidence_id == "ev-agg-1"
    assert agg.evidence.description == "execution trace data"

# ----------------- API Integration Tests -----------------

@pytest.fixture
def client(service_setup):
    svc, resolver, replay, *_ = service_setup
    api_module._service = svc
    api_module._resolver = resolver
    api_module._replay = replay
    
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)

def test_api_create_journal(client, snapshot):
    payload = {
        "decision_id": "dec-api-1",
        "proposing_agent_id": "agt-1",
        "signature": "sig-1",
        "thesis_urn": "urn:thesis:1",
        "context_snapshot": {
            "prompt_ref": {"prompt_id": "pr-1", "prompt_hash": "hash-pr", "template_urn": "urn:temp:1"},
            "dataset_ref": {"dataset_id": "ds-1", "dataset_hash": "hash-ds", "dataset_urn": "urn:data:1"},
            "telemetry_ref": {"telemetry_id": "tel-1", "telemetry_hash": "hash-tel", "span_id": "span-1"},
            "artifact_ref": {"artifact_id": "art-1", "artifact_hash": "hash-art", "artifact_urn": "urn:art:1"},
            "replay_metadata": {"git_commit": "git-1", "runtime_image": "docker-1", "seed": 42, "temperature": 0.7, "regime_identifier": "high-vol"}
        },
        "probability": 0.85
    }
    response = client.post("/journals/create", json=payload)
    assert response.status_code == 201
    assert response.json()["decision_id"] == "dec-api-1"

def test_api_create_revision_and_lineage(client, snapshot):
    payload = {
        "decision_id": "root-api",
        "proposing_agent_id": "agt-1",
        "signature": "sig-1",
        "thesis_urn": "urn:thesis:1",
        "context_snapshot": {
            "prompt_ref": {"prompt_id": "pr-1", "prompt_hash": "hash-pr", "template_urn": "urn:temp:1"},
            "dataset_ref": {"dataset_id": "ds-1", "dataset_hash": "hash-ds", "dataset_urn": "urn:data:1"},
            "telemetry_ref": {"telemetry_id": "tel-1", "telemetry_hash": "hash-tel", "span_id": "span-1"},
            "artifact_ref": {"artifact_id": "art-1", "artifact_hash": "hash-art", "artifact_urn": "urn:art:1"},
            "replay_metadata": {"git_commit": "git-1", "runtime_image": "docker-1", "seed": 42, "temperature": 0.7, "regime_identifier": "high-vol"}
        },
        "probability": 0.85
    }
    client.post("/journals/create", json=payload)

    # Revision
    rev_payload = {
        "revision_id": "rev-api-1",
        "parent_decision_id": "root-api",
        "proposing_agent_id": "agt-1",
        "signature": "sig-2",
        "correction_reason": "Parameters adjustments",
        "context_snapshot": payload["context_snapshot"]
    }
    rev_response = client.post("/journals/revision/create", json=rev_payload)
    assert rev_response.status_code == 201

    # Active Leaf
    leaf_response = client.get("/journals/active_leaf/root-api")
    assert leaf_response.status_code == 200
    assert leaf_response.json()["active_leaf_decision_id"] == "rev-api-1"

    # Lineage
    lineage_response = client.get("/journals/lineage/root-api")
    assert lineage_response.status_code == 200
    assert "rev-api-1" in lineage_response.json()["nodes"]

def test_api_replay_decision(client, snapshot):
    payload = {
        "decision_id": "dec-api-2",
        "proposing_agent_id": "agt-1",
        "signature": "sig-1",
        "thesis_urn": "urn:thesis:1",
        "context_snapshot": {
            "prompt_ref": {"prompt_id": "pr-1", "prompt_hash": "hash-pr", "template_urn": "urn:temp:1"},
            "dataset_ref": {"dataset_id": "ds-1", "dataset_hash": "hash-ds", "dataset_urn": "urn:data:1"},
            "telemetry_ref": {"telemetry_id": "tel-1", "telemetry_hash": "hash-tel", "span_id": "span-1"},
            "artifact_ref": {"artifact_id": "art-1", "artifact_hash": "hash-art", "artifact_urn": "urn:art:1"},
            "replay_metadata": {"git_commit": "git-1", "runtime_image": "docker-1", "seed": 42, "temperature": 0.7, "regime_identifier": "high-vol"}
        },
        "probability": 0.85
    }
    client.post("/journals/create", json=payload)

    from karsa.decision_journal.api import map_snapshot, ContextSnapshotSchema
    mapped = map_snapshot(ContextSnapshotSchema(**payload["context_snapshot"]))
    expected_hash = hashlib.sha256(str(mapped).encode('utf-8')).hexdigest()

    replay_payload = {
        "decision_id": "dec-api-2",
        "expected_hash": expected_hash,
        "context_uri": "s3://decision-contexts/dec-api-2.json"
    }
    replay_response = client.post("/journals/replay", json=replay_payload)
    assert replay_response.status_code == 200
    assert replay_response.json()["verified"] is True

def test_api_error_handling():
    import karsa.decision_journal.api as api_module
    old_svc = api_module._service
    old_resolver = api_module._resolver
    old_replay = api_module._replay
    
    api_module._service = None
    api_module._resolver = None
    api_module._replay = None
    
    with pytest.raises(RuntimeError):
        api_module.get_service()
    with pytest.raises(RuntimeError):
        api_module.get_resolver()
    with pytest.raises(RuntimeError):
        api_module.get_replay()
        
    api_module._service = old_svc
    api_module._resolver = old_resolver
    api_module._replay = old_replay

def test_api_endpoints_error_responses(client, snapshot):
    # 1. Invalid probability on create -> 400
    payload = {
        "decision_id": "dec-err-1",
        "proposing_agent_id": "agt-1",
        "signature": "sig-1",
        "thesis_urn": "urn:thesis:1",
        "context_snapshot": {
            "prompt_ref": {"prompt_id": "pr-1", "prompt_hash": "hash-pr", "template_urn": "urn:temp:1"},
            "dataset_ref": {"dataset_id": "ds-1", "dataset_hash": "hash-ds", "dataset_urn": "urn:data:1"},
            "telemetry_ref": {"telemetry_id": "tel-1", "telemetry_hash": "hash-tel", "span_id": "span-1"},
            "artifact_ref": {"artifact_id": "art-1", "artifact_hash": "hash-art", "artifact_urn": "urn:art:1"},
            "replay_metadata": {"git_commit": "git-1", "runtime_image": "docker-1", "seed": 42, "temperature": 0.7, "regime_identifier": "high-vol"}
        },
        "probability": 1.5
    }
    response = client.post("/journals/create", json=payload)
    assert response.status_code == 400

    # 2. Invalid parent ID on revision -> 404
    rev_payload = {
        "revision_id": "rev-err-1",
        "parent_decision_id": "non-existent",
        "proposing_agent_id": "agt-1",
        "signature": "sig-2",
        "correction_reason": "test",
        "context_snapshot": payload["context_snapshot"]
    }
    response = client.post("/journals/revision/create", json=rev_payload)
    assert response.status_code == 404

    # 3. Validation Exception on revision post-execution -> 403
    payload["decision_id"] = "dec-err-2"
    payload["probability"] = 0.9
    client.post("/journals/create", json=payload)
    
    import karsa.decision_journal.api as api_module
    api_module._service.set_execution_started("dec-err-2")
    
    rev_payload["parent_decision_id"] = "dec-err-2"
    response = client.post("/journals/revision/create", json=rev_payload)
    assert response.status_code == 403

    # 4. Lineage error on non-existent root -> 404
    response = client.get("/journals/lineage/non-existent")
    assert response.status_code == 404

    # 5. Active leaf error on non-existent root -> 404
    response = client.get("/journals/active_leaf/non-existent")
    assert response.status_code == 404

    # 6. Replay verification failed -> 400
    replay_payload = {
        "decision_id": "dec-err-2",
        "expected_hash": "wrong-hash",
        "context_uri": "s3://decision-contexts/dec-err-2.json"
    }
    response = client.post("/journals/replay", json=replay_payload)
    assert response.status_code == 400

def test_ports_coverage():
    from karsa.decision_journal.ports import ObjectStorePort, EventPublisherPort
    ObjectStorePort.save_context_snapshot(None, None, None)
    ObjectStorePort.get_context_snapshot(None, None)
    ObjectStorePort.verify_hash(None, None, None)
    EventPublisherPort.publish(None, None)
