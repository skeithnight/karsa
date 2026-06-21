"""Residual calculation tests — Sprint-09."""
import pytest

from karsa.attribution_engine.domain.entities.attribution_contribution import AttributionContribution
from karsa.attribution_engine.domain.value_objects.attribution_evidence import AttributionEvidence


def _make_contribution(dimension, bps):
    return AttributionContribution(
        contribution_id=f"c-{dimension}",
        dimension=dimension,
        target_urn="w1",
        evidence=AttributionEvidence(source_type="TEST", source_id="e1", data_points={}, explanation="test"),
        contribution_bps=bps,
        contribution_pct=bps / 100,
        quality_score=0.5,
        quality_provenance={"source": "SYSTEM_DEFAULT", "score": 0.5},
    )


class TestResidualCalculation:
    def test_residual_positive(self):
        """When contributions < total_variance, residual is positive."""
        contributions = [
            _make_contribution("THESIS", 30),
            _make_contribution("EXECUTION", 25),
            _make_contribution("ALLOCATION", 20),
            _make_contribution("REGIME", 15),
        ]
        total_variance = 100.0
        sum_contributions = sum(c.contribution_bps for c in contributions)
        residual = total_variance - sum_contributions
        assert residual == 10.0

    def test_residual_zero(self):
        """When contributions = total_variance, residual is zero."""
        contributions = [
            _make_contribution("THESIS", 40),
            _make_contribution("EXECUTION", 30),
            _make_contribution("ALLOCATION", 20),
            _make_contribution("REGIME", 10),
        ]
        total_variance = 100.0
        sum_contributions = sum(c.contribution_bps for c in contributions)
        residual = total_variance - sum_contributions
        assert residual == 0.0

    def test_residual_negative(self):
        """When contributions > total_variance, residual is negative."""
        contributions = [
            _make_contribution("THESIS", 50),
            _make_contribution("EXECUTION", 40),
            _make_contribution("ALLOCATION", 30),
            _make_contribution("REGIME", 20),
        ]
        total_variance = 100.0
        sum_contributions = sum(c.contribution_bps for c in contributions)
        residual = total_variance - sum_contributions
        assert residual == -40.0

    def test_contributions_plus_residual_equals_total(self):
        """ADR-095: contributions + residual must equal total_variance."""
        contributions = [
            _make_contribution("THESIS", 30),
            _make_contribution("EXECUTION", 25),
            _make_contribution("ALLOCATION", 20),
            _make_contribution("REGIME", 15),
        ]
        total_variance = 100.0
        sum_contributions = sum(c.contribution_bps for c in contributions)
        residual = total_variance - sum_contributions
        assert sum_contributions + residual == total_variance
