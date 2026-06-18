import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from karsa.shared.persistence.base import Base
from karsa.evidence.domain.models import PromotedEvidence
from karsa.evidence.infrastructure.storage.repositories import EvidenceRepository
from karsa.evidence.infrastructure.storage.models import PromotedEvidenceModel # for Base metadata

engine = create_engine('sqlite:///:memory:')
Session = sessionmaker(bind=engine)

def setup_module(module):
    Base.metadata.create_all(engine)

def teardown_module(module):
    Base.metadata.drop_all(engine)

def test_evidence_repository_integration():
    session = Session()
    repo = EvidenceRepository(session)
    
    payload = {"k": "v"}
    ext_time = datetime(2026, 6, 17, 10, 0, 0)
    ev = PromotedEvidence("blob-2", "prov-2", "asset-2", ext_time, payload)
    
    repo.add(ev)
    session.commit()
    
    # test get
    fetched = repo.get(ev.evidence_id)
    assert fetched is not None
    assert fetched.payload_hash == ev.payload_hash
    assert fetched.payload == payload
    
    # test get_by_hash
    fetched2 = repo.get_by_hash(ev.payload_hash)
    assert fetched2 is not None
    assert fetched2.evidence_id == ev.evidence_id
    
    # test none
    assert repo.get("fake") is None
    assert repo.get_by_hash("fake") is None
