"""AttributionContribution tests — Sprint-09."""
import pytest

from karsa.attribution_engine.domain.entities.attribution_contribution import AttributionContribution
from karsa.attribution_engine.domain.value_objects.attribution_evidence import AttributionEvidence


def _make_contribution(**overrides):
    defaults = dict(
        contribution_id="c1",
        dimension="THESIS",
        target_urn="worker-1",
        evidence=AttributionEvidence(source_type="TEST", source_id="eval-1", data_points={}, explanation="test"),
        contribution_bps=30.0,
        contribution_pct=0.3,
        quality_score=0.7,
        quality_provenance={"source": "SYSTEM_DEFAULT", "score": 0.7},
    )
    defaults.update(overrides)
    return AttributionContribution(**defaults)


class TestAttributionContribution:
    def test_valid_contribution(self):
        c = _make_contribution()
        assert c.contribution_id == "c1"
        assert c.dimension == "THESIS"

    def test_empty_contribution_id_raises(self):
        with pytest.raises(AssertionError):
            _make_contribution(contribution_id="")

    def test_invalid_dimension_raises(self):
        with pytest.raises(AssertionError):
            _make_contribution(dimension="INVALID")

    def test_quality_score_validation(self):
        with pytest.raises(AssertionError):
            _make_contribution(quality_score=1.5)

    def test_quality_source_validation(self):
        with pytest.raises(AssertionError):
            _make_contribution(quality_provenance={"source": "INVALID", "score": 0.5})

    def test_valid_dimensions(self):
        for dim in ("THESIS", "EXECUTION", "ALLOCATION", "REGIME", "RESIDUAL"):
            c = _make_contribution(dimension=dim)
            assert c.dimension == dim

    def test_frozen(self):
        c = _make_contribution()
        with pytest.raises(AttributeError):
            c.contribution_id = "changed"

    def test_quality_provenance_structure(self):
        provenance = {"source": "THESIS_ENGINE", "score": 0.8}
        c = _make_contribution(quality_provenance=provenance)
        assert c.quality_provenance["source"] == "THESIS_ENGINE"
        assert c.quality_provenance["score"] == 0.8
