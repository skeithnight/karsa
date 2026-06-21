"""Tests for Capability Engine child entities -- Sprint-11."""

import pytest

from karsa.capability_engine.domain.entities.evolution_finding import (
    EvolutionFinding,
)
from karsa.capability_engine.domain.entities.evolution_attribution_ref import (
    EvolutionAttributionRef,
)


class TestEvolutionFinding:
    def test_valid_finding(self):
        f = EvolutionFinding(
            finding_id="f-001",
            finding_type="CONCERN",
            severity="HIGH",
            dimension="THESIS",
            description="Low thesis alignment",
        )
        assert f.finding_id == "f-001"

    def test_frozen(self):
        f = EvolutionFinding(
            finding_id="f-001",
            finding_type="CONCERN",
            severity="HIGH",
            dimension="THESIS",
            description="Low thesis alignment",
        )
        with pytest.raises(AttributeError):
            f.finding_id = "new"  # type: ignore[misc]

    def test_missing_finding_id(self):
        with pytest.raises(ValueError, match="finding_id is required"):
            EvolutionFinding(
                finding_id="",
                finding_type="CONCERN",
                severity="HIGH",
                dimension="THESIS",
                description="test",
            )._validate()

    def test_missing_finding_type(self):
        with pytest.raises(ValueError, match="finding_type is required"):
            EvolutionFinding(
                finding_id="f-001",
                finding_type="",
                severity="HIGH",
                dimension="THESIS",
                description="test",
            )._validate()

    def test_missing_severity(self):
        with pytest.raises(ValueError, match="severity is required"):
            EvolutionFinding(
                finding_id="f-001",
                finding_type="CONCERN",
                severity="",
                dimension="THESIS",
                description="test",
            )._validate()

    def test_missing_dimension(self):
        with pytest.raises(ValueError, match="dimension is required"):
            EvolutionFinding(
                finding_id="f-001",
                finding_type="CONCERN",
                severity="HIGH",
                dimension="",
                description="test",
            )._validate()

    def test_missing_description(self):
        with pytest.raises(ValueError, match="description is required"):
            EvolutionFinding(
                finding_id="f-001",
                finding_type="CONCERN",
                severity="HIGH",
                dimension="THESIS",
                description="",
            )._validate()


class TestEvolutionAttributionRef:
    def test_valid_ref(self):
        r = EvolutionAttributionRef(
            contribution_id="c-001",
            dimension="THESIS",
            contribution_bps=150.0,
            quality_score=0.85,
        )
        assert r.contribution_id == "c-001"

    def test_frozen(self):
        r = EvolutionAttributionRef(
            contribution_id="c-001",
            dimension="THESIS",
            contribution_bps=150.0,
            quality_score=0.85,
        )
        with pytest.raises(AttributeError):
            r.contribution_id = "new"  # type: ignore[misc]

    def test_missing_contribution_id(self):
        with pytest.raises(ValueError, match="contribution_id is required"):
            EvolutionAttributionRef(
                contribution_id="",
                dimension="THESIS",
                contribution_bps=150.0,
                quality_score=0.85,
            )._validate()

    def test_missing_dimension(self):
        with pytest.raises(ValueError, match="dimension is required"):
            EvolutionAttributionRef(
                contribution_id="c-001",
                dimension="",
                contribution_bps=150.0,
                quality_score=0.85,
            )._validate()

    def test_quality_score_out_of_range(self):
        with pytest.raises(ValueError, match="quality_score must be 0.0-1.0"):
            EvolutionAttributionRef(
                contribution_id="c-001",
                dimension="THESIS",
                contribution_bps=150.0,
                quality_score=1.5,
            )._validate()
