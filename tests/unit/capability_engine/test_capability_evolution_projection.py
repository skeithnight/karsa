"""Tests for CapabilityEvolutionProjection DTO -- Sprint-11. Wave-5."""

import pytest
from datetime import datetime

from karsa.capability_engine.projections.capability_evolution_projection import (
    CapabilityEvolutionProjection,
)


class TestCapabilityEvolutionProjection:
    """DTO validation tests."""

    def test_valid_projection(self):
        p = CapabilityEvolutionProjection(
            capability_family_id="f-001",
            evaluation_id="e-001",
            capability_urn="urn:karsa:capability:ns:test:v1",
        )
        assert p.capability_family_id == "f-001"
        assert p.total_evolutions == 0

    def test_frozen(self):
        p = CapabilityEvolutionProjection(
            capability_family_id="f-001",
            evaluation_id="e-001",
            capability_urn="urn:karsa:capability:ns:test:v1",
        )
        with pytest.raises(AttributeError):
            p.total_evolutions = 5

    def test_missing_family_id(self):
        with pytest.raises(ValueError, match="capability_family_id"):
            CapabilityEvolutionProjection(
                capability_family_id="",
                evaluation_id="e-001",
                capability_urn="urn:test",
            )

    def test_missing_evaluation_id(self):
        with pytest.raises(ValueError, match="evaluation_id"):
            CapabilityEvolutionProjection(
                capability_family_id="f-001",
                evaluation_id="",
                capability_urn="urn:test",
            )

    def test_missing_capability_urn(self):
        with pytest.raises(ValueError, match="capability_urn"):
            CapabilityEvolutionProjection(
                capability_family_id="f-001",
                evaluation_id="e-001",
                capability_urn="",
            )

    def test_negative_total_evolutions(self):
        with pytest.raises(ValueError, match="total_evolutions"):
            CapabilityEvolutionProjection(
                capability_family_id="f-001",
                evaluation_id="e-001",
                capability_urn="urn:test",
                total_evolutions=-1,
            )

    def test_negative_positive_evolutions(self):
        with pytest.raises(ValueError, match="positive_evolutions"):
            CapabilityEvolutionProjection(
                capability_family_id="f-001",
                evaluation_id="e-001",
                capability_urn="urn:test",
                positive_evolutions=-1,
            )

    def test_negative_negative_evolutions(self):
        with pytest.raises(ValueError, match="negative_evolutions"):
            CapabilityEvolutionProjection(
                capability_family_id="f-001",
                evaluation_id="e-001",
                capability_urn="urn:test",
                negative_evolutions=-1,
            )

    def test_trigger_breakdown_default(self):
        p = CapabilityEvolutionProjection(
            capability_family_id="f-001",
            evaluation_id="e-001",
            capability_urn="urn:test",
        )
        assert p.trigger_type_breakdown == {}

    def test_full_projection(self):
        now = datetime.utcnow()
        p = CapabilityEvolutionProjection(
            capability_family_id="f-001",
            evaluation_id="e-001",
            capability_urn="urn:test",
            total_evolutions=5,
            trigger_type_breakdown={"REVIEW_FINDING": 3, "ATTRIBUTION_INSIGHT": 2},
            positive_evolutions=3,
            negative_evolutions=2,
            avg_score_change_bps=150.0,
            last_score_change_bps=300.0,
            last_evolution_type="SCORE_ADJUSTMENT",
            last_evaluated_at=now,
        )
        assert p.total_evolutions == 5
        assert p.trigger_type_breakdown["REVIEW_FINDING"] == 3
        assert p.avg_score_change_bps == 150.0
