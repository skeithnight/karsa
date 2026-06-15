import pytest
from decimal import Decimal
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from src.karsa.regime.domain.value_objects import (
    SignalConfidenceScore, RegimeEvidence, RegimeHorizon,
    RegimeClassification, RegimeMethodologyManifest
)
from src.karsa.regime.domain.events import (
    RegimeSnapshotCreatedEvent, RegimeTransitionRecordedEvent,
    RegimeSnapshotSupersededEvent, RegimeSnapshotInvalidatedEvent
)
from src.karsa.regime.domain.models import (
    RegimeSession, RegimeSnapshot, RegimeTransition,
    IllegalStateTransitionError, TerminalStateError
)
from src.karsa.regime.domain.lineage import (
    reconstruct_transition_lineage, reconstruct_snapshot_lineage, LineageCycleError
)

def test_signal_confidence_score_valid():
    score = SignalConfidenceScore(Decimal('0.5'))
    assert score.value == Decimal('0.5')
    assert "SignalConfidenceScore" in repr(score)
    assert score.canonical_meaning() == "Weighted Signal Confidence"
    assert "probability" in score.prohibited_interpretations()
    assert score.to_dict() == {"value": "0.5"}

def test_signal_confidence_score_invalid():
    with pytest.raises(ValueError):
        SignalConfidenceScore(Decimal('-0.1'))
    with pytest.raises(ValueError):
        SignalConfidenceScore(Decimal('1.1'))

def test_regime_evidence():
    evidence = RegimeEvidence(
        evidence_type="TREND",
        evidence_value=Decimal('1.0'),
        evidence_weight=Decimal('0.8'),
        evidence_contribution=Decimal('0.8'),
        evidence_methodology_urn="urn:method",
        evidence_policy_hash="hash_p",
        evidence_manifest_hash="hash_m"
    )
    d = evidence.to_dict()
    assert d['evidence_type'] == "TREND"

def test_regime_horizon():
    h = RegimeHorizon("urn:30D", 30)
    assert h.to_dict()['days'] == 30

def test_regime_classification():
    c = RegimeClassification("BULL", "LOW", "HIGH")
    assert c.to_dict()['market_regime'] == "BULL"

def test_regime_methodology_manifest():
    m = RegimeMethodologyManifest.create(
        "urn:m", "phash", "v1", ["ehash1", "ehash2"]
    )
    assert m.regime_methodology_urn == "urn:m"
    assert m.regime_policy_hash == "phash"
    assert m.regime_manifest_hash is not None
    assert m.to_dict()['regime_strategy_version'] == "v1"

def test_domain_events():
    now = datetime.now()
    e = RegimeSnapshotCreatedEvent(
        event_id="e1", correlation_id="c1", causation_id="ca1", occurred_at=now,
        snapshot_urn="urn:s1", segment_urn="urn:seg1", horizon_urn="urn:h1",
        snapshot_date="2026-06-15", regime_manifest_hash="hash"
    )
    d = e.to_dict()
    assert d['event_id'] == "e1"
    
    e2 = RegimeTransitionRecordedEvent(
        event_id="e2", correlation_id="c2", causation_id="ca2", occurred_at=now,
        transition_urn="urn:t1", from_regime_market="BULL", to_regime_market="BEAR",
        supersedes_transition_urn=None, transition_manifest_hash="hash"
    )
    assert e2.to_dict()['from_regime_market'] == "BULL"

    e3 = RegimeSnapshotSupersededEvent(
        event_id="e3", correlation_id="c3", causation_id="ca3", occurred_at=now,
        snapshot_urn="urn:s1", superseded_by_snapshot_urn="urn:s2"
    )
    assert e3.to_dict()['superseded_by_snapshot_urn'] == "urn:s2"

    e4 = RegimeSnapshotInvalidatedEvent(
        event_id="e4", correlation_id="c4", causation_id="ca4", occurred_at=now,
        snapshot_urn="urn:s1", invalidating_version=2
    )
    assert e4.to_dict()['invalidating_version'] == 2

def test_regime_session_lifecycle():
    s = RegimeSession("urn:sess")
    assert s.state == "INITIATED"
    s.start_analyzing()
    assert s.state == "ANALYZING"
    assert s.aggregate_version == 2
    s.complete_classification()
    assert s.state == "CLASSIFIED"
    assert s.aggregate_version == 3
    s.seal()
    assert s.state == "SEALED"
    assert s.aggregate_version == 4
    
    with pytest.raises(TerminalStateError):
        s.ensure_not_terminal()
        
    with pytest.raises(IllegalStateTransitionError):
        s.start_analyzing()

def test_regime_session_invalid_transitions():
    s = RegimeSession("urn:sess")
    with pytest.raises(IllegalStateTransitionError):
        s.complete_classification()
    with pytest.raises(IllegalStateTransitionError):
        s.seal()

def test_regime_snapshot():
    c = RegimeClassification("BULL", "LOW", "HIGH")
    score = SignalConfidenceScore(Decimal('1.0'))
    s = RegimeSnapshot(
        snapshot_urn="urn:s1", segment_urn="urn:seg", horizon_urn="urn:h",
        snapshot_date="2026-06-15", regime_classification=c, confidence_score=score,
        regime_manifest_hash="hash", evidence_manifest_hash="ehash", methodology_metadata={}
    )
    assert s.natural_key == ("urn:seg", "urn:h", "2026-06-15")

def test_regime_transition():
    c1 = RegimeClassification("BULL", "LOW", "HIGH")
    c2 = RegimeClassification("BEAR", "HIGH", "LOW")
    t = RegimeTransition("urn:t1", c1, c2, "hash")
    t.supersede("urn:t2")
    assert t.supersedes_transition_urn == "urn:t2"
    assert t.aggregate_version == 2
    t.invalidate("urn:inv")
    assert t.invalidates_transition_urn == "urn:inv"
    assert t.aggregate_version == 3

def test_reconstruct_transition_lineage():
    c1 = RegimeClassification("BULL", "LOW", "HIGH")
    t1 = RegimeTransition("urn:t1", c1, c1, "hash", supersedes_transition_urn="urn:t2")
    t2 = RegimeTransition("urn:t2", c1, c1, "hash", supersedes_transition_urn=None)
    
    lineage = reconstruct_transition_lineage([t1, t2], "urn:t1")
    assert len(lineage) == 2
    assert lineage[0].transition_urn == "urn:t1"
    assert lineage[1].transition_urn == "urn:t2"

def test_reconstruct_transition_lineage_cycle():
    c1 = RegimeClassification("BULL", "LOW", "HIGH")
    t1 = RegimeTransition("urn:t1", c1, c1, "hash", supersedes_transition_urn="urn:t2")
    t2 = RegimeTransition("urn:t2", c1, c1, "hash", supersedes_transition_urn="urn:t1")
    
    with pytest.raises(LineageCycleError):
        reconstruct_transition_lineage([t1, t2], "urn:t1")

@dataclass
class DummySnapshot:
    snapshot_urn: str
    supersedes_snapshot_urn: Optional[str] = None

def test_reconstruct_snapshot_lineage():
    s1 = DummySnapshot("urn:s1", supersedes_snapshot_urn="urn:s2")
    s2 = DummySnapshot("urn:s2", supersedes_snapshot_urn=None)
    lineage = reconstruct_snapshot_lineage([s1, s2], "urn:s1")
    assert len(lineage) == 2

def test_reconstruct_snapshot_lineage_cycle():
    s1 = DummySnapshot("urn:s1", supersedes_snapshot_urn="urn:s2")
    s2 = DummySnapshot("urn:s2", supersedes_snapshot_urn="urn:s1")
    with pytest.raises(LineageCycleError):
        reconstruct_snapshot_lineage([s1, s2], "urn:s1")
