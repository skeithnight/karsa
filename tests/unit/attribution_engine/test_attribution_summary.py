"""AttributionSummary tests — Sprint-09."""
import pytest

from karsa.attribution_engine.domain.value_objects.attribution_summary import AttributionSummary


class TestAttributionSummary:
    def test_valid_summary(self):
        s = AttributionSummary(
            total_variance_bps=100.0,
            thesis_contribution_bps=30.0,
            execution_contribution_bps=25.0,
            allocation_contribution_bps=20.0,
            regime_contribution_bps=15.0,
            residual_bps=10.0,
            interaction_effects_bps=0,
            attribution_confidence=0.7,
            explanation="test",
        )
        s.validate()

    def test_variance_mismatch_raises(self):
        s = AttributionSummary(
            total_variance_bps=100.0,
            thesis_contribution_bps=30.0,
            execution_contribution_bps=25.0,
            allocation_contribution_bps=20.0,
            regime_contribution_bps=15.0,
            residual_bps=5.0,  # sum = 95, not 100
            interaction_effects_bps=0,
            attribution_confidence=0.7,
            explanation="test",
        )
        with pytest.raises(AssertionError, match="must equal total_variance"):
            s.validate()

    def test_confidence_out_of_range_raises(self):
        s = AttributionSummary(
            total_variance_bps=100.0,
            thesis_contribution_bps=30.0,
            execution_contribution_bps=25.0,
            allocation_contribution_bps=20.0,
            regime_contribution_bps=15.0,
            residual_bps=10.0,
            interaction_effects_bps=0,
            attribution_confidence=1.5,
            explanation="test",
        )
        with pytest.raises(AssertionError):
            s.validate()
