"""Integration: Algorithm Version Change -- Sprint-11. Wave-7.

Scenario 9: History under v1.0, change to v2.0.
Verify: history preserved, algorithm_version propagated.
ADR-134.
"""

import pytest

from karsa.capability_engine.application.capability_scoring_service import (
    ScoringCommand,
)
from karsa.capability_engine.integration.capability_engine_bootstrap import bootstrap
from karsa.capability_engine.integration.capability_engine_fixture import (
    make_components,
)


@pytest.fixture
def ctx():
    return bootstrap()


class TestAlgorithmVersionChange:
    """ADR-134: Algorithm versioning across evaluations."""

    def test_algorithm_version_in_history(self, ctx):
        # v1.0 evaluations
        for i in range(3):
            cmd = ScoringCommand(
                capability_family_id="int-family-001",
                evaluation_id=f"int-eval-v1-{i+1:03d}",
                evaluation_sequence=i + 1,
                capability_version_id="int-ver-001",
                score=0.5 + i * 0.05,
                components=make_components(),
                algorithm_version="v1.0",
            )
            ctx.scoring_service.record_evaluation(cmd)

        # v2.0 evaluation
        cmd = ScoringCommand(
            capability_family_id="int-family-001",
            evaluation_id="int-eval-v2-001",
            evaluation_sequence=4,
            capability_version_id="int-ver-002",
            score=0.8,
            components=make_components(),
            algorithm_version="v2.0",
        )
        ctx.scoring_service.record_evaluation(cmd)

        # Verify history has both versions
        history = ctx.score_history_repo.get_by_family("int-family-001")
        assert len(history) == 4

        v1_entries = [e for e in history if e.algorithm_version == "v1.0"]
        v2_entries = [e for e in history if e.algorithm_version == "v2.0"]
        assert len(v1_entries) == 3
        assert len(v2_entries) == 1

    def test_aggregate_tracks_latest_algorithm(self, ctx):
        # v1.0
        cmd = ScoringCommand(
            capability_family_id="int-family-001",
            evaluation_id="int-eval-001",
            evaluation_sequence=1,
            capability_version_id="int-ver-001",
            score=0.6,
            components=make_components(),
            algorithm_version="v1.0",
        )
        ctx.scoring_service.record_evaluation(cmd)

        # v2.0
        cmd = ScoringCommand(
            capability_family_id="int-family-001",
            evaluation_id="int-eval-002",
            evaluation_sequence=2,
            capability_version_id="int-ver-002",
            score=0.8,
            components=make_components(),
            algorithm_version="v2.0",
        )
        ctx.scoring_service.record_evaluation(cmd)

        hs = ctx.health_score_repo.get_by_family_id("int-family-001")
        assert hs.algorithm_version == "v2.0"

    def test_version_boundary_preserved_in_timeseries(self, ctx):
        # v1.0
        cmd = ScoringCommand(
            capability_family_id="int-family-001",
            evaluation_id="int-eval-001",
            evaluation_sequence=1,
            capability_version_id="int-ver-v1",
            score=0.6,
            components=make_components(),
            algorithm_version="v1.0",
        )
        ctx.scoring_service.record_evaluation(cmd)

        # v2.0
        cmd = ScoringCommand(
            capability_family_id="int-family-001",
            evaluation_id="int-eval-002",
            evaluation_sequence=2,
            capability_version_id="int-ver-v2",
            score=0.8,
            components=make_components(),
            algorithm_version="v2.0",
        )
        ctx.scoring_service.record_evaluation(cmd)

        # Rebuild timeseries
        ctx.projection_service.rebuild_timeseries_projection()

        ts = ctx.timeseries_projection_repo.get_by_family("int-family-001")
        assert len(ts) == 2

        v1_entries = [
            e for e in ts if e["capability_version_id"] == "int-ver-v1"
        ]
        v2_entries = [
            e for e in ts if e["capability_version_id"] == "int-ver-v2"
        ]
        assert len(v1_entries) == 1
        assert len(v2_entries) == 1
        assert v1_entries[0]["algorithm_version"] == "v1.0"
        assert v2_entries[0]["algorithm_version"] == "v2.0"
