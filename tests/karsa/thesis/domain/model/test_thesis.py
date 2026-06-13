import pytest
from datetime import datetime, timezone
from karsa.thesis.domain.model.thesis import ActiveThesis, ThesisState, InvalidTransitionError, ThesisReview

def test_thesis_initial_state():
    thesis = ActiveThesis(thesis_id="T-1", author="quant_1", created_at=datetime.now(timezone.utc))
    assert thesis.state == ThesisState.ACTIVE

def test_valid_degrade_transition():
    thesis = ActiveThesis("T-1", "quant_1", datetime.now(timezone.utc))
    thesis.degrade()
    assert thesis.state == ThesisState.DEGRADED

def test_valid_review_transition():
    thesis = ActiveThesis("T-1", "quant_1", datetime.now(timezone.utc))
    thesis.degrade()
    thesis.request_review()
    assert thesis.state == ThesisState.UNDER_REVIEW

def test_valid_confirm_transition():
    thesis = ActiveThesis("T-1", "quant_1", datetime.now(timezone.utc))
    thesis.request_review()
    review = ThesisReview("R-1", "reviewer_1", datetime.now(timezone.utc), "APPROVE", "Looks good")
    thesis.confirm(review)
    assert thesis.state == ThesisState.CONFIRMED
    assert len(thesis.reviews) == 1

def test_valid_invalidate_transition():
    thesis = ActiveThesis("T-1", "quant_1", datetime.now(timezone.utc))
    thesis.invalidate("Core assumptions broken")
    assert thesis.state == ThesisState.INVALIDATED

def test_valid_retire_transition():
    thesis = ActiveThesis("T-1", "quant_1", datetime.now(timezone.utc))
    thesis.retire("Strategy reached end of life")
    assert thesis.state == ThesisState.RETIRED

def test_invalid_transition_confirm_from_active():
    thesis = ActiveThesis("T-1", "quant_1", datetime.now(timezone.utc))
    review = ThesisReview("R-1", "reviewer_1", datetime.now(timezone.utc), "APPROVE", "Looks good")
    with pytest.raises(InvalidTransitionError):
        thesis.confirm(review)

def test_invalid_transition_from_invalidated():
    thesis = ActiveThesis("T-1", "quant_1", datetime.now(timezone.utc))
    thesis.invalidate("Broken")
    with pytest.raises(InvalidTransitionError):
        thesis.degrade()
    with pytest.raises(InvalidTransitionError):
        thesis.request_review()
    with pytest.raises(InvalidTransitionError):
        thesis.retire("Retiring after invalidated")
