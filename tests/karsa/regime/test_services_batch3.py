import pytest
from decimal import Decimal

from src.karsa.regime.infrastructure.storage.in_memory_repositories import (
    InMemoryRegimeSnapshotRepository, InMemoryRegimeTransitionRepository
)
from src.karsa.regime.domain.value_objects import (
    RegimeClassification, SignalConfidenceScore, RegimeEvidence, RegimeMethodologyManifest
)
from src.karsa.regime.application.regime_services import (
    RegimeClassificationService, RegimeTransitionService, RegimeReplayService, 
    RegimeProjectionService, RegimeInvalidationService, DriftError
)
from src.karsa.regime.domain.models import RegimeTransition

@pytest.fixture
def snapshot_repo():
    return InMemoryRegimeSnapshotRepository()

@pytest.fixture
def transition_repo():
    return InMemoryRegimeTransitionRepository()

def test_classification_service(snapshot_repo):
    svc = RegimeClassificationService(snapshot_repo)
    c = RegimeClassification("BULL", "LOW", "HIGH")
    conf = SignalConfidenceScore(Decimal('0.8'))
    ev = RegimeEvidence("TREND", Decimal('1'), Decimal('1'), Decimal('1'), "urn:m", "hash_p", "hash_m")
    
    snap = svc.classify(
        segment_urn="seg1", horizon_urn="hor1", snapshot_date="2026-06-15",
        classification=c, confidence=conf, evidences=[ev],
        methodology_urn="urn:m", policy_hash="p", strategy_version="v1", metadata={}
    )
    
    assert snap.segment_urn == "seg1"
    assert snapshot_repo.find_by_urn(snap.snapshot_urn) is not None

def test_transition_hysteresis_suppression(snapshot_repo, transition_repo):
    svc = RegimeClassificationService(snapshot_repo)
    t_svc = RegimeTransitionService(snapshot_repo, transition_repo)
    
    c_bull = RegimeClassification("BULL", "LOW", "HIGH")
    c_bear = RegimeClassification("BEAR", "HIGH", "LOW")
    conf = SignalConfidenceScore(Decimal('0.8'))
    ev = RegimeEvidence("TREND", Decimal('1'), Decimal('1'), Decimal('1'), "urn:m", "hash_p", "hash_m")
    
    # 06-10 to 06-12 BULL
    for i in range(10, 13):
        svc.classify(
            segment_urn="seg1", horizon_urn="hor1", snapshot_date=f"2026-06-{i}",
            classification=c_bull, confidence=conf, evidences=[ev],
            methodology_urn="urn:m", policy_hash="p", strategy_version="v1", metadata={}
        )
        
    # 06-13 BEAR
    svc.classify(
        segment_urn="seg1", horizon_urn="hor1", snapshot_date="2026-06-13",
        classification=c_bear, confidence=conf, evidences=[ev],
        methodology_urn="urn:m", policy_hash="p", strategy_version="v1", metadata={}
    )
    
    # Hysteresis window = 2. We only have 1 BEAR snapshot. Should suppress.
    t = t_svc.evaluate_hysteresis("seg1", "hor1", "2026-06-13", confirmation_window=2)
    assert t is None

def test_transition_hysteresis_confirmation(snapshot_repo, transition_repo):
    svc = RegimeClassificationService(snapshot_repo)
    t_svc = RegimeTransitionService(snapshot_repo, transition_repo)
    
    c_bull = RegimeClassification("BULL", "LOW", "HIGH")
    c_bear = RegimeClassification("BEAR", "HIGH", "LOW")
    conf = SignalConfidenceScore(Decimal('0.8'))
    ev = RegimeEvidence("TREND", Decimal('1'), Decimal('1'), Decimal('1'), "urn:m", "hash_p", "hash_m")
    
    # 06-10 BULL
    svc.classify("seg1", "hor1", "2026-06-10", c_bull, conf, [ev], "urn", "p", "v1", {})
    
    # 06-11, 06-12 BEAR (window=2)
    svc.classify("seg1", "hor1", "2026-06-11", c_bear, conf, [ev], "urn", "p", "v1", {})
    svc.classify("seg1", "hor1", "2026-06-12", c_bear, conf, [ev], "urn", "p", "v1", {})
    
    t = t_svc.evaluate_hysteresis("seg1", "hor1", "2026-06-12", confirmation_window=2)
    assert t is not None
    assert t.to_regime.market_regime == "BEAR"
    assert transition_repo.find_by_urn(t.transition_urn) is not None

def test_replay_service(snapshot_repo):
    svc = RegimeClassificationService(snapshot_repo)
    c_bull = RegimeClassification("BULL", "LOW", "HIGH")
    conf = SignalConfidenceScore(Decimal('0.8'))
    ev = RegimeEvidence("TREND", Decimal('1'), Decimal('1'), Decimal('1'), "urn:m", "hash_p", "hash_m")
    
    snap = svc.classify("seg1", "hor1", "2026-06-10", c_bull, conf, [ev], "urn:m", "p", "v1", {})
    
    # Expected manifest
    m = RegimeMethodologyManifest.create(
        "urn:m", "p", "v1", [snap.evidence_manifest_hash] # simplified, just matching what classify does
    ) # actually classify does hashing on the evidence dict
    
    rep = RegimeReplayService()
    # If the expected matches, it passes.
    # Replay logic constructs the hash inside verify.
    # The actual evidence hash computation logic needs to match.
    import hashlib, json
    e_hash = hashlib.sha256(json.dumps(ev.to_dict(), separators=(',', ':'), sort_keys=True).encode()).hexdigest()
    m2 = RegimeMethodologyManifest.create("urn:m", "p", "v1", [e_hash])
    
    rep.verify(snap, m2, [ev])
    
    # Drift
    ev_drift = RegimeEvidence("TREND", Decimal('2'), Decimal('1'), Decimal('1'), "urn:m", "hash_p", "hash_m")
    with pytest.raises(DriftError):
        rep.verify(snap, m2, [ev_drift])

def test_projection_service(snapshot_repo, transition_repo):
    svc = RegimeClassificationService(snapshot_repo)
    proj = RegimeProjectionService(snapshot_repo, transition_repo)
    
    c_bull = RegimeClassification("BULL", "LOW", "HIGH")
    conf = SignalConfidenceScore(Decimal('0.8'))
    ev = RegimeEvidence("TREND", Decimal('1'), Decimal('1'), Decimal('1'), "urn:m", "hash_p", "hash_m")
    
    svc.classify("seg2", "hor2", "2026-06-10", c_bull, conf, [ev], "urn", "p", "v1", {})
    
    cur = proj.get_current_regime("seg2", "hor2")
    assert cur.market_regime == "BULL"
    
    hist = proj.get_historical_projection("seg2", "hor2")
    assert len(hist) == 1

def test_invalidation_service(snapshot_repo, transition_repo):
    inv = RegimeInvalidationService(snapshot_repo, transition_repo)
    c_bull = RegimeClassification("BULL", "LOW", "HIGH")
    t1 = RegimeTransition("urn:t1", c_bull, c_bull, "h", "urn:t2")
    t2 = RegimeTransition("urn:t2", c_bull, c_bull, "h", None)
    transition_repo.save(t1)
    transition_repo.save(t2)
    
    inv.invalidate_transition_chain("urn:t1", "urn:inv")
    
    # Should invalidate both
    assert transition_repo.find_by_urn("urn:t1").invalidates_transition_urn == "urn:inv"
    assert transition_repo.find_by_urn("urn:t2").invalidates_transition_urn == "urn:inv"

