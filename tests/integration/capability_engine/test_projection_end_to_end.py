"""Integration: Projection Rebuild -- Sprint-11. Wave-7.

Scenario 4: Persisted data -> Projection rebuild.
ADR-126, ADR-131, ADR-133, ADR-135, ADR-137.
"""

import pytest

from karsa.capability_engine.domain.aggregates.capability_health_score import (
    CapabilityHealthScore,
)
from karsa.capability_engine.domain.value_objects.enums import (
    EvolutionStatus,
    ScoreTrend,
)
from karsa.capability_engine.domain.value_objects.score_history_entry import (
    ScoreHistoryEntry,
)
from karsa.capability_engine.integration.capability_engine_bootstrap import bootstrap
from karsa.capability_engine.integration.capability_engine_fixture import (
    make_evolution,
    make_registry_entry,
    make_components,
)


@pytest.fixture
def ctx():
    return bootstrap()


class TestProjectionRebuild:
    """End-to-end: Source data -> TRUNCATE + INSERT projections."""

    def test_evolution_projection_rebuild(self, ctx):
        # Setup: evolution + canonical registry
        evo = make_evolution()
        ctx.evolution_repo.save(evo)
        ctx.version_registry.save(make_registry_entry(
            evolution_id=evo.evolution_id,
        ))

        result = ctx.projection_service.rebuild_evolution_projection()
        assert result.rows_written == 1

        summary = ctx.evolution_projection_repo.get_evolution_summary(
            evo.capability_family_id
        )
        assert summary is not None
        assert summary["total_evolutions"] == 1

    def test_health_projection_rebuild(self, ctx):
        # Setup: health score aggregate
        ctx.health_score_repo.save(CapabilityHealthScore(
            health_score_id="int-hs-001",
            capability_family_id="int-family-001",
            current_score=0.75,
            score_components=make_components(),
            evaluation_count=5,
            algorithm_version="v1.0",
        ))

        result = ctx.projection_service.rebuild_health_projection()
        assert result.rows_written == 1

        proj = ctx.health_projection_repo.get_health_score("int-family-001")
        assert proj is not None
        assert proj["current_score"] == 0.75
        assert proj["algorithm_version"] == "v1.0"
        assert proj["score_trend"] == ScoreTrend.UNKNOWN.value

    def test_timeseries_projection_rebuild(self, ctx):
        # Setup: health score + history
        ctx.health_score_repo.save(CapabilityHealthScore(
            health_score_id="int-hs-001",
            capability_family_id="int-family-001",
        ))
        for i in range(3):
            ctx.score_history_repo.append(ScoreHistoryEntry(
                capability_family_id="int-family-001",
                evaluation_id=f"int-eval-{i+1:03d}",
                evaluation_sequence=i + 1,
                capability_version_id="int-ver-001",
                score=0.5 + i * 0.1,
                algorithm_version="v1.0",
            ))

        result = ctx.projection_service.rebuild_timeseries_projection()
        assert result.rows_written == 3

        ts = ctx.timeseries_projection_repo.get_by_family("int-family-001")
        assert len(ts) == 3
        assert ts[0]["evaluation_sequence"] == 1
        assert ts[2]["evaluation_sequence"] == 3

    def test_rebuild_all(self, ctx):
        results = ctx.projection_service.rebuild_all()
        assert len(results) == 3
        names = {r.projection_name for r in results}
        assert "capability_evolution_projection" in names
        assert "capability_health_projection" in names
        assert "capability_score_timeseries_projection" in names

    def test_rebuild_idempotent(self, ctx):
        """ADR-126: TRUNCATE + INSERT produces same result on repeated rebuild."""
        ctx.health_score_repo.save(CapabilityHealthScore(
            health_score_id="int-hs-001",
            capability_family_id="int-family-001",
            current_score=0.6,
        ))

        r1 = ctx.projection_service.rebuild_health_projection()
        r2 = ctx.projection_service.rebuild_health_projection()

        assert r1.rows_written == r2.rows_written == 1
        assert len(ctx.health_projection_repo._store) == 1

    def test_canonical_filtering(self, ctx):
        """ADR-133: Only canonical records contribute."""
        evo = make_evolution()
        ctx.evolution_repo.save(evo)
        # Register as SUPERSEDED, not CANONICAL
        ctx.version_registry.save(make_registry_entry(
            evolution_id=evo.evolution_id,
            evolution_status="SUPERSEDED",
        ))

        result = ctx.projection_service.rebuild_evolution_projection()
        assert result.rows_written == 0
