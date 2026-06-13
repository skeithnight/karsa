import pytest
from unittest.mock import MagicMock
from karsa.shared.domain.identity import OriginatorIdentity
from karsa.thesis.application.service.thesis_application_service import ThesisApplicationService
from karsa.thesis.application.commands import (
    ProposeThesisCommand, GovernanceDecisionPayload, RecordReviewCommand
)
from karsa.thesis.domain.model.value_objects import (
    HypothesisStructure, ConfidenceModel, TimeHorizon,
    TimeClassification, ConfidenceSource, ThesisReviewRecord, ThesisState
)
from karsa.thesis.domain.model.thesis import Thesis

@pytest.fixture
def mock_uow():
    uow = MagicMock()
    uow.__enter__ = MagicMock(return_value=uow)
    uow.__exit__ = MagicMock(return_value=None)
    uow.outbox_repository = MagicMock()
    return uow

@pytest.fixture
def mock_repo():
    return MagicMock()

def create_valid_thesis():
    originator = OriginatorIdentity("o1", "HUMAN", "v1")
    hypothesis = HypothesisStructure("H1", "Bull", "Bear", ["A1"], "Out", ["I1"], ["S1"])
    confidence = ConfidenceModel(0.8, None, ConfidenceSource.MANUAL, "2024")
    time_horizon = TimeHorizon("2024-01-01", "2024-12-31", TimeClassification.SHORT_TERM)
    return Thesis("t1", originator, hypothesis, confidence, time_horizon, [])

def test_propose_thesis_saves_outbox(mock_uow, mock_repo):
    service = ThesisApplicationService(mock_uow, mock_repo)
    originator = OriginatorIdentity("o1", "HUMAN", "v1")
    hypothesis = HypothesisStructure("H1", "Bull", "Bear", ["A1"], "Out", ["I1"], ["S1"])
    confidence = ConfidenceModel(0.8, None, ConfidenceSource.MANUAL, "2024")
    time_horizon = TimeHorizon("2024-01-01", "2024-12-31", TimeClassification.SHORT_TERM)
    
    cmd = ProposeThesisCommand(
        thesis_id="t1",
        originator=originator,
        hypothesis=hypothesis,
        confidence=confidence,
        time_horizon=time_horizon,
        research_lineage=[]
    )
    
    service.propose_thesis(cmd)
    
    mock_repo.save.assert_called_once()
    saved_thesis = mock_repo.save.call_args[0][0]
    assert saved_thesis.state == ThesisState.PROPOSED
    
    mock_uow.outbox_repository.save.assert_called_once()
    outbox_record = mock_uow.outbox_repository.save.call_args[0][0]
    assert "ThesisProposedEvent" in outbox_record.payload

def test_governance_approval_transition(mock_uow, mock_repo):
    service = ThesisApplicationService(mock_uow, mock_repo)
    thesis = create_valid_thesis()
    thesis.propose()
    mock_repo.get_by_id.return_value = thesis
    
    cmd = GovernanceDecisionPayload("t1", "APPROVED", "r1", "2024", "Looks good")
    service.apply_governance_decision(cmd)
    
    assert thesis.state == ThesisState.ACTIVE
    mock_uow.outbox_repository.save.assert_called_once()

def test_governance_rejection_transition(mock_uow, mock_repo):
    service = ThesisApplicationService(mock_uow, mock_repo)
    thesis = create_valid_thesis()
    thesis.propose()
    mock_repo.get_by_id.return_value = thesis
    
    cmd = GovernanceDecisionPayload("t1", "REJECTED", "r1", "2024", "No")
    service.apply_governance_decision(cmd)
    
    assert thesis.state == ThesisState.REJECTED
    mock_uow.outbox_repository.save.assert_called_once()

def test_record_review_no_aggregate_mutation(mock_uow, mock_repo):
    service = ThesisApplicationService(mock_uow, mock_repo)
    thesis = create_valid_thesis()
    thesis.propose()
    initial_version = thesis.aggregate_version
    mock_repo.get_by_id.return_value = thesis
    
    review = ThesisReviewRecord("Periodic", "Standard", "r1", "2024")
    cmd = RecordReviewCommand("t1", review)
    service.record_review(cmd)
    
    assert thesis.aggregate_version == initial_version # Version should not change
    mock_repo.save.assert_not_called() # Thesis should not be saved
    mock_uow.outbox_repository.save.assert_called_once() # Outbox event should be saved
