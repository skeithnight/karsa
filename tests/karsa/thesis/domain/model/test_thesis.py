import pytest
from karsa.shared.domain.identity import OriginatorIdentity
from karsa.thesis.domain.model.thesis import Thesis
from karsa.thesis.domain.model.value_objects import (
    HypothesisStructure, ConfidenceModel, TimeHorizon, ResearchReference,
    TimeClassification, ConfidenceSource, ThesisState, ThesisContributor, ContributionRole
)
from karsa.thesis.domain.model.exceptions import (
    InvalidThesisStateTransitionError, InvalidConfidenceError, DuplicateContributorError
)

def create_valid_thesis():
    originator = OriginatorIdentity("o1", "HUMAN", "v1")
    hypothesis = HypothesisStructure("H1", "Bull", "Bear", ["A1"], "Out", ["I1"], ["S1"])
    confidence = ConfidenceModel(0.8, None, ConfidenceSource.MANUAL, "2024")
    time_horizon = TimeHorizon("2024-01-01", "2024-12-31", TimeClassification.SHORT_TERM)
    return Thesis("t1", originator, hypothesis, confidence, time_horizon, [])

def test_thesis_cannot_return_to_draft():
    thesis = create_valid_thesis()
    thesis.propose()
    assert thesis.state == ThesisState.PROPOSED
    thesis.activate()
    assert thesis.state == ThesisState.ACTIVE
    
    with pytest.raises(InvalidThesisStateTransitionError):
        thesis.propose()
        
    thesis = create_valid_thesis()
    thesis.propose()
    thesis.activate()
    assert thesis.state == ThesisState.ACTIVE

def test_activate_requires_proposed():
    thesis = create_valid_thesis()
    with pytest.raises(InvalidThesisStateTransitionError):
        thesis.activate()

def test_reject_requires_proposed():
    thesis = create_valid_thesis()
    with pytest.raises(InvalidThesisStateTransitionError):
        thesis.reject()

def test_version_increment_on_mutation():
    thesis = create_valid_thesis()
    initial_version = thesis.aggregate_version
    thesis.propose()
    assert thesis.aggregate_version == initial_version + 1

def test_confidence_bounds():
    thesis = create_valid_thesis()
    with pytest.raises(InvalidConfidenceError):
        bad_conf = ConfidenceModel(1.5, None, ConfidenceSource.MANUAL, "2024")
        thesis.update_confidence(bad_conf)

def test_contributor_role_validation():
    thesis = create_valid_thesis()
    with pytest.raises(ValueError, match="Role AUTHOR is reserved"):
        thesis.add_contributor(ThesisContributor("c1", "HUMAN", "AUTHOR"))

def test_snapshot_immutability():
    from karsa.thesis.domain.model.snapshot import ThesisSnapshotFactory
    thesis = create_valid_thesis()
    snapshot = ThesisSnapshotFactory.build(thesis)
    # The snapshot is a frozen dataclass, setting an attribute should raise FrozenInstanceError
    from dataclasses import FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        snapshot.thesis_id = "t2"
