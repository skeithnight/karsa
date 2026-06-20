"""Tests for ReviewHorizon value object — Sprint-06 Wave-2."""
import pytest

from karsa.allocation.domain.model.value_objects import ReviewHorizon


class TestReviewHorizon:
    def test_valid_review_horizon(self):
        rh = ReviewHorizon(
            review_date="2026-07-20T00:00:00Z",
            review_criteria="Evaluate if cumulative alpha exceeds 50bps",
        )
        assert rh.review_date == "2026-07-20T00:00:00Z"
        assert rh.auto_expire is False

    def test_empty_review_criteria_raises(self):
        with pytest.raises(ValueError, match="review_criteria cannot be empty"):
            ReviewHorizon(review_date="2026-07-20", review_criteria="")

    def test_whitespace_review_criteria_raises(self):
        with pytest.raises(ValueError, match="review_criteria cannot be empty"):
            ReviewHorizon(review_date="2026-07-20", review_criteria="   ")

    def test_auto_expire_default_false(self):
        rh = ReviewHorizon(review_date="2026-07-20", review_criteria="Test criteria")
        assert rh.auto_expire is False

    def test_auto_expire_set_true(self):
        rh = ReviewHorizon(
            review_date="2026-07-20",
            review_criteria="Test criteria",
            auto_expire=True,
        )
        assert rh.auto_expire is True

    def test_frozen_immutability(self):
        rh = ReviewHorizon(review_date="2026-07-20", review_criteria="Test criteria")
        with pytest.raises(AttributeError):
            rh.review_criteria = "Changed"
