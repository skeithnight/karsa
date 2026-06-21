"""Tests for CapabilityScoreTimeseriesProjection DTO -- Sprint-11. ADR-137."""

import pytest
from datetime import datetime

from karsa.capability_engine.projections.capability_score_timeseries_projection import (
    CapabilityScoreTimeseriesProjection,
)


class TestCapabilityScoreTimeseriesProjection:
    """DTO validation and ADR-137 compliance tests."""

    def test_valid_projection(self):
        p = CapabilityScoreTimeseriesProjection(
            capability_family_id="f-001",
            capability_version_id="v-001",
            evaluation_id="e-001",
            evaluation_sequence=1,
            score=0.75,
            algorithm_version="v1.0",
            recorded_at=datetime.utcnow(),
        )
        assert p.capability_family_id == "f-001"
        assert p.score == 0.75

    def test_frozen(self):
        p = CapabilityScoreTimeseriesProjection(
            capability_family_id="f-001",
            capability_version_id="v-001",
            evaluation_id="e-001",
            evaluation_sequence=1,
            score=0.75,
            algorithm_version="v1.0",
            recorded_at=datetime.utcnow(),
        )
        with pytest.raises(AttributeError):
            p.score = 0.9

    def test_missing_family_id(self):
        with pytest.raises(ValueError, match="capability_family_id"):
            CapabilityScoreTimeseriesProjection(
                capability_family_id="",
                capability_version_id="v-001",
                evaluation_id="e-001",
                evaluation_sequence=1,
                score=0.5,
                algorithm_version="v1.0",
                recorded_at=datetime.utcnow(),
            )

    def test_missing_version_id(self):
        with pytest.raises(ValueError, match="capability_version_id"):
            CapabilityScoreTimeseriesProjection(
                capability_family_id="f-001",
                capability_version_id="",
                evaluation_id="e-001",
                evaluation_sequence=1,
                score=0.5,
                algorithm_version="v1.0",
                recorded_at=datetime.utcnow(),
            )

    def test_missing_evaluation_id(self):
        with pytest.raises(ValueError, match="evaluation_id"):
            CapabilityScoreTimeseriesProjection(
                capability_family_id="f-001",
                capability_version_id="v-001",
                evaluation_id="",
                evaluation_sequence=1,
                score=0.5,
                algorithm_version="v1.0",
                recorded_at=datetime.utcnow(),
            )

    def test_score_out_of_range(self):
        with pytest.raises(ValueError, match="score"):
            CapabilityScoreTimeseriesProjection(
                capability_family_id="f-001",
                capability_version_id="v-001",
                evaluation_id="e-001",
                evaluation_sequence=1,
                score=1.5,
                algorithm_version="v1.0",
                recorded_at=datetime.utcnow(),
            )

    def test_negative_sequence(self):
        with pytest.raises(ValueError, match="evaluation_sequence"):
            CapabilityScoreTimeseriesProjection(
                capability_family_id="f-001",
                capability_version_id="v-001",
                evaluation_id="e-001",
                evaluation_sequence=-1,
                score=0.5,
                algorithm_version="v1.0",
                recorded_at=datetime.utcnow(),
            )

    def test_missing_algorithm_version(self):
        with pytest.raises(ValueError, match="algorithm_version"):
            CapabilityScoreTimeseriesProjection(
                capability_family_id="f-001",
                capability_version_id="v-001",
                evaluation_id="e-001",
                evaluation_sequence=1,
                score=0.5,
                algorithm_version="",
                recorded_at=datetime.utcnow(),
            )

    def test_adr137_version_boundary_preserved(self):
        """ADR-137: capability_version_id tracks version boundaries."""
        p = CapabilityScoreTimeseriesProjection(
            capability_family_id="f-001",
            capability_version_id="ver-v2-uuid",
            evaluation_id="e-001",
            evaluation_sequence=5,
            score=0.8,
            algorithm_version="v2.0",
            recorded_at=datetime.utcnow(),
        )
        assert p.capability_version_id == "ver-v2-uuid"

    def test_adr136_sequence_ordering(self):
        """ADR-136: evaluation_sequence is monotonic."""
        entries = []
        for i in range(5):
            entries.append(
                CapabilityScoreTimeseriesProjection(
                    capability_family_id="f-001",
                    capability_version_id="v-001",
                    evaluation_id=f"e-{i:03d}",
                    evaluation_sequence=i + 1,
                    score=0.5 + i * 0.05,
                    algorithm_version="v1.0",
                    recorded_at=datetime.utcnow(),
                )
            )
        sequences = [e.evaluation_sequence for e in entries]
        assert sequences == [1, 2, 3, 4, 5]
