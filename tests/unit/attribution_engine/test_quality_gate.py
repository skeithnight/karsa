"""Quality gate tests — Sprint-09."""
import pytest

from karsa.attribution_engine.domain.value_objects.attribution_quality import AttributionQuality


class TestQualityGate:
    def test_sufficient_quality(self):
        q = AttributionQuality(quality_score=0.5, data_completeness=1.0, decomposition_confidence=0.5)
        assert q.is_sufficient is True

    def test_insufficient_quality(self):
        q = AttributionQuality(quality_score=0.2, data_completeness=0.5, decomposition_confidence=0.1)
        assert q.is_sufficient is False

    def test_boundary_quality(self):
        q = AttributionQuality(quality_score=0.3, data_completeness=1.0, decomposition_confidence=0.3)
        assert q.is_sufficient is True

    def test_quality_score_validation(self):
        with pytest.raises(AssertionError):
            AttributionQuality(quality_score=1.5, data_completeness=1.0, decomposition_confidence=0.5).validate()

    def test_completeness_validation(self):
        with pytest.raises(AssertionError):
            AttributionQuality(quality_score=0.5, data_completeness=-0.1, decomposition_confidence=0.5).validate()
