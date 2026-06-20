import pytest
from datetime import datetime
from karsa.evidence.domain.models import PromotedEvidence
from karsa.evidence.application.dtos import EvidencePromotionRequestDTO
from karsa.evidence.application.services import EvidencePromotionService

class DummyUoW:
    def __enter__(self): pass
    def __exit__(self, *args): pass
    def commit(self): pass
    def rollback(self): pass

class DummyEvidenceRepo:
    def __init__(self):
        self.items = {}
        self.hashes = {}

    def add(self, ev):
        self.items[ev.evidence_id] = ev
        self.hashes[ev.payload_hash] = ev

    def get(self, evidence_id):
        ev = self.items.get(evidence_id)
        if ev:
            ev._domain_events.clear()
        return ev

    def get_by_hash(self, phash):
        ev = self.hashes.get(phash)
        if ev:
            ev._domain_events.clear()
        return ev

def test_evidence_aggregate():
    payload = {"price": 100}
    ext_time = datetime(2026, 6, 17, 10, 0, 0)
    ev = PromotedEvidence("blob-1", "prov-1", "asset-1", ext_time, payload)
    
    assert ev.evidence_id is not None
    assert ev.aggregate_id == ev.evidence_id
    assert ev.source_blob_id == "blob-1"
    assert ev.extracted_at == ext_time
    assert ev.payload_hash is not None
    
    events = ev.pull_domain_events()
    assert len(events) == 1
    assert events[0].event_name == "EvidencePromotedEvent"
    assert events[0].aggregate_type == "PromotedEvidence"
    assert events[0].extracted_at == ext_time

def test_evidence_service_promotion():
    repo = DummyEvidenceRepo()
    uow = DummyUoW()
    svc = EvidencePromotionService(repo, uow)
    
    req = EvidencePromotionRequestDTO(
        source_blob_id="blob-x",
        provider_id="prov-x",
        asset_id="asset-x",
        extracted_at=datetime(2026, 6, 17, 10, 0, 0),
        payload={"data": "test"}
    )
    
    res = svc.promote_evidence(req)
    assert res.evidence_id is not None
    assert res.payload_hash is not None
    assert "evidence:idx:prov-x:" in res.evidence_urn
    
    # Test idempotency via hash
    res2 = svc.promote_evidence(req)
    assert res2.evidence_id == res.evidence_id
    
    # Test fetch
    fetched = svc.get_evidence(res.evidence_id)
    assert fetched is not None
    assert fetched.payload_hash == res.payload_hash
    assert fetched.extracted_at == res.extracted_at
    
    assert svc.get_evidence("fake") is None

def test_deterministic_identity():
    payload = {"k": "v"}
    ev1 = PromotedEvidence("blob", "prov", "asset", datetime(2026,1,1), payload)
    ev2 = PromotedEvidence("blob", "prov", "asset", datetime(2026,1,2), payload)
    
    # Despite different extraction/promotion dates, same payload -> same hash -> same evidence_id
    assert ev1.payload_hash == ev2.payload_hash
    assert ev1.evidence_id == ev2.evidence_id

def test_concurrent_duplication_protection():
    payload = {"data": "race"}
    repo = DummyEvidenceRepo()
    
    class ThrowingUoW:
        def __enter__(self): pass
        def __exit__(self, *args): pass
        def commit(self):
            # Simulate the other thread having inserted it right before our commit
            repo.add(PromotedEvidence("b", "p", "a", datetime.utcnow(), payload))
            import sqlite3
            raise sqlite3.IntegrityError("UNIQUE constraint failed: promoted_evidence.payload_hash")
        def rollback(self): pass
        
    uow = ThrowingUoW()
    svc = EvidencePromotionService(repo, uow)
    
    # Do not pre-populate repo so we bypass the initial check
    req = EvidencePromotionRequestDTO("b", "p", "a", datetime.utcnow(), payload)
    res = svc.promote_evidence(req)
    
    # Service should catch IntegrityError and return the existing one from the repo
    assert res.payload_hash is not None
