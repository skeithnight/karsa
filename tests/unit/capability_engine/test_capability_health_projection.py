"""Tests for CapabilityHealthProjection DTO -- Sprint-11. Wave-5. ADR-131."""

import pytest
from datetime import datetime

from karsa.capability_engine.domain.value_objects.enums import ScoreTrend
from karsa.capability_engine.projections.capability_health_projection import (
    CapabilityHealthProjection,
)


class TestCapabilityHealthProjection:
    """DTO validation and ADR-131 compliance tests."""

    def test_valid_projection(self):
        p = CapabilityHealthProjection(
            capability_family_id="f-001",
            capability_urn="urn:karsa:capability:ns:test:v1",
        )
        assert p.capability_family_id == "f-001"

    def test_adr131_default_score(self):
        """ADR-131: Default score = 0.5."""
        p = CapabilityHealthProjection(
            capability_family_id="f-001",
            capability_urn="urn:test",
        )
        assert p.current_score == 0.5

    def test_adr131_default_data_completeness(self):
        """ADR-131: Default data_completeness = 0.0."""
        p = CapabilityHealthProjection(
            capability_family_id="f-001",
            capability_urn="urn:test",
        )
        assert p.data_completeness == 0.0

    def test_adr131_default_score_trend(self):
        """ADR-131: Default score_trend = UNKNOWN."""
        p = CapabilityHealthProjection(
            capability_family_id="f-001",
            capability_urn="urn:test",
        )
        assert p.score_trend == ScoreTrend.UNKNOWN.value

    def test_frozen(self):
        p = CapabilityHealthProjection(
            capability_family_id="f-001",
            capability_urn="urn:test",
        )
        with pytest.raises(AttributeError):
            p.current_score = 0.8

    def test_missing_family_id(self):
        with pytest.raises(ValueError, match="capability_family_id"):
            CapabilityHealthProjection(
                capability_family_id="",
                capability_urn="urn:test",
            )

    def test_missing_capability_urn(self):
        with pytest.raises(ValueError, match="capability_urn"):
            CapabilityHealthProjection(
                capability_family_id="f-001",
                capability_urn="",
            )

    def test_score_out_of_range_high(self):
        with pytest.raises(ValueError, match="current_score"):
            CapabilityHealthProjection(
                capability_family_id="f-001",
                capability_urn="urn:test",
                current_score=1.5,
            )

    def test_score_out_of_range_low(self):
        with pytest.raises(ValueError, match="current_score"):
            CapabilityHealthProjection(
                capability_family_id="f-001",
                capability_urn="urn:test",
                current_score=-0.1,
            )

    def test_data_completeness_out_of_range(self):
        with pytest.raises(ValueError, match="data_completeness"):
            CapabilityHealthProjection(
                capability_family_id="f-001",
                capability_urn="urn:test",
                data_completeness=1.5,
            )

    def test_negative_evaluation_count(self):
        with pytest.raises(ValueError, match="evaluation_count"):
            CapabilityHealthProjection(
                capability_family_id="f-001",
                capability_urn="urn:test",
                evaluation_count=-1,
            )

    def test_negative_consecutive_low_scores(self):
        with pytest.raises(ValueError, match="consecutive_low_scores"):
            CapabilityHealthProjection(
                capability_family_id="f-001",
                capability_urn="urn:test",
                consecutive_low_scores=-1,
            )

    def test_negative_consecutive_high_scores(self):
        with pytest.raises(ValueError, match="consecutive_high_scores"):
            CapabilityHealthProjection(
                capability_family_id="f-001",
                capability_urn="urn:test",
                consecutive_high_scores=-1,
            )

    def test_null_prevention_defaults(self):
        """ADR-131: All fields have non-null defaults."""
        p = CapabilityHealthProjection(
            capability_family_id="f-001",
            capability_urn="urn:test",
        )
        assert p.current_score is not None
        assert p.algorithm_version is not None
        assert p.execution_quality_score is not None
        assert p.attribution_alignment_score is not None
        assert p.review_sentiment_score is not None
        assert p.regime_fitness_score is not None
        assert p.evaluation_count is not None
        assert p.data_completeness is not None
        assert p.score_trend is not None
        assert p.lifecycle_state is not None
        assert p.consecutive_low_scores is not None
        assert p.consecutive_high_scores is not None

    def test_full_projection(self):
        now = datetime.utcnow()
        p = CapabilityHealthProjection(
            capability_family_id="f-001",
            capability_urn="urn:test:v2",
            current_score=0.75,
            algorithm_version="v2.0",
            execution_quality_score=0.8,
            attribution_alignment_score=0.7,
            review_sentiment_score=0.6,
            regime_fitness_score=0.9,
            evaluation_count=10,
            data_completeness=1.0,
            score_trend=ScoreTrend.IMPROVING.value,
            lifecycle_state="ACTIVE",
            last_evaluated_at=now,
            consecutive_low_scores=0,
            consecutive_high_scores=2,
        )
        assert p.current_score == 0.75
        assert p.algorithm_version == "v2.0"
        assert p.execution_quality_score == 0.8
        assert p.data_completeness == 1.0
        assert p.score_trend == ScoreTrend.IMPROVING.value
        assert p.consecutive_high_scores == 2
