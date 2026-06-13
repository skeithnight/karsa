import pytest
from karsa.shared.domain.identity import OriginatorIdentity
from karsa.thesis.domain.model.thesis import Thesis
from karsa.thesis.domain.model.value_objects import (
    HypothesisStructure, ConfidenceModel, TimeHorizon, TimeClassification, ConfidenceSource
)
from karsa.thesis.events.factory import ThesisEventFactory

def create_valid_thesis():
    originator = OriginatorIdentity("o1", "HUMAN", "v1")
    hypothesis = HypothesisStructure("H1", "Bull", "Bear", ["A1"], "Out", ["I1"], ["S1"])
    confidence = ConfidenceModel(0.8, None, ConfidenceSource.MANUAL, "2024")
    time_horizon = TimeHorizon("2024-01-01", "2024-12-31", TimeClassification.SHORT_TERM)
    return Thesis("t1", originator, hypothesis, confidence, time_horizon, [])

def test_proposed_event_generation():
    thesis = create_valid_thesis()
    thesis.propose()
    event = ThesisEventFactory.build_proposed(thesis)
    
    assert event.event_type == "ThesisProposedEvent"
    assert event.aggregate_type == "Thesis"
    assert event.aggregate_id == "t1"
    assert event.correlation_id == "t1"
    assert event.aggregate_version == 2 # 1 (init) + 1 (propose)

def test_correlation_and_causation_propagation():
    thesis = create_valid_thesis()
    event = ThesisEventFactory.build_rejected(thesis, causation_id="cause-1")
    assert event.correlation_id == "t1"
    assert event.causation_id == "cause-1"
