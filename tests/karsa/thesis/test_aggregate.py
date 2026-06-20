import pytest
from karsa.thesis.domain.models import Thesis, LifecycleState
from karsa.thesis.domain.events import ThesisProposedEvent, ThesisActivatedEvent

def test_thesis_lifecycle_and_ownership():
    t = Thesis("urn:karsa:thesis:1", "urn:karsa:author:1", "urn:karsa:regime:1")
    assert t.current_status == LifecycleState.PROPOSED
    assert t.confidence == 0.0
    
    # Test proposed
    ev = ThesisProposedEvent(payload={
        "title": "Test Thesis",
        "confidence": 0.8,
        "assumptions": [{"urn": "urn:a:1", "statement": "Rates go down"}]
    })
    t.apply(ev)
    
    assert t.title == "Test Thesis"
    assert t.confidence == 0.8
    assert len(t.assumptions) == 1
    assert t.assumptions[0].statement == "Rates go down"
    assert t.current_status == LifecycleState.PROPOSED
    
    # Test activated
    ev2 = ThesisActivatedEvent(payload={"activator_urn": "urn:gov:1", "activation_rationale": "Looks good"})
    t.apply(ev2)
    assert t.current_status == LifecycleState.ACTIVE
    assert len(t.governance_trail) == 1
    assert t.governance_trail[0]["actor"] == "urn:gov:1"
