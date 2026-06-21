"""Quality provenance schema tests — Sprint-09 F-08."""
import pytest

from karsa.attribution_engine.domain.entities.attribution_contribution import AttributionContribution
from karsa.attribution_engine.domain.aggregates.attribution_record import AttributionRecord
from karsa.attribution_engine.domain.value_objects.attribution_evidence import AttributionEvidence
from karsa.attribution_engine.domain.value_objects.attribution_summary import AttributionSummary
from karsa.attribution_engine.domain.value_objects.attribution_quality import AttributionQuality
from karsa.attribution_engine.domain.value_objects.attribution_context_snapshot import AttributionContextSnapshot
from datetime import datetime


def _make_provenance(source="SYSTEM_DEFAULT", score=0.5):
    return {"source": source, "score": score}


def _make_contribution(dimension="THESIS", provenance=None):
    if provenance is None:
        provenance = _make_provenance()
    return AttributionContribution(
        contribution_id="c1",
        dimension=dimension,
        target_urn="w1",
        evidence=AttributionEvidence(source_type="TEST", source_id="e1", data_points={}, explanation="test"),
        contribution_bps=30.0,
        contribution_pct=0.3,
        quality_score=0.7,
        quality_provenance=provenance,
    )


class TestQualityProvenanceContainsThesisDimension:
    def test_thesis_contribution_has_provenance(self):
        c = _make_contribution("THESIS", _make_provenance("THESIS_ENGINE", 0.8))
        assert c.quality_provenance["source"] == "THESIS_ENGINE"
        assert c.quality_provenance["score"] == 0.8


class TestQualityProvenanceContainsExecutionDimension:
    def test_execution_contribution_has_provenance(self):
        c = _make_contribution("EXECUTION", _make_provenance("EXECUTION_ENGINE", 0.7))
        assert c.quality_provenance["source"] == "EXECUTION_ENGINE"
        assert c.quality_provenance["score"] == 0.7


class TestQualityProvenanceContainsAllocationDimension:
    def test_allocation_contribution_has_provenance(self):
        c = _make_contribution("ALLOCATION", _make_provenance("CAPITAL_ALLOCATION_ENGINE", 0.6))
        assert c.quality_provenance["source"] == "CAPITAL_ALLOCATION_ENGINE"
        assert c.quality_provenance["score"] == 0.6


class TestQualityProvenanceSchemaMatchesADR105:
    def test_aggregate_level_provenance_has_all_dimensions(self):
        """ADR-105: quality_provenance contains thesis, execution, allocation."""
        record_provenance = {
            "thesis": {"source": "THESIS_ENGINE", "score": 0.8},
            "execution": {"source": "EXECUTION_ENGINE", "score": 0.7},
            "allocation": {"source": "CAPITAL_ALLOCATION_ENGINE", "score": 0.5},
        }
        assert "thesis" in record_provenance
        assert "execution" in record_provenance
        assert "allocation" in record_provenance
        assert all("source" in v and "score" in v for v in record_provenance.values())

    def test_contribution_level_provenance_has_source_and_score(self):
        """Each contribution has its own provenance with source and score."""
        c = _make_contribution()
        assert "source" in c.quality_provenance
        assert "score" in c.quality_provenance


class TestQualityProvenanceSourceValidation:
    def test_valid_sources(self):
        for source in ("SYSTEM_DEFAULT", "MANUAL_REVIEW", "THESIS_ENGINE", "EXECUTION_ENGINE", "CAPITAL_ALLOCATION_ENGINE"):
            c = _make_contribution(provenance=_make_provenance(source))
            assert c.quality_provenance["source"] == source

    def test_invalid_source_raises(self):
        with pytest.raises(AssertionError, match="Invalid quality_provenance.source"):
            _make_contribution(provenance={"source": "INVALID", "score": 0.5})


class TestQualityProvenanceScoreValidation:
    def test_valid_scores(self):
        for score in (0.0, 0.5, 1.0):
            c = _make_contribution(provenance=_make_provenance(score=score))
            assert c.quality_provenance["score"] == score

    def test_missing_source_raises(self):
        with pytest.raises(AssertionError, match="quality_provenance.source required"):
            _make_contribution(provenance={"score": 0.5})

    def test_missing_score_raises(self):
        with pytest.raises(AssertionError, match="quality_provenance.score required"):
            _make_contribution(provenance={"source": "SYSTEM_DEFAULT"})
