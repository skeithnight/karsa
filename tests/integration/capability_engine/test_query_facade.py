"""Tests for CapabilityQueryFacade -- Sprint-11. Wave-8.

Scenarios:
- Capability Health Query -> DTO
- Evolution History Query -> DTO
- Timeseries Query -> DTO
- Governance Status Query -> DTO

Verifies: Projection data returned without exposing internals.
"""

import pytest

from karsa.capability_engine.contracts.capability_health_dto import (
    CapabilityHealthDTO,
)
from karsa.capability_engine.contracts.capability_evolution_dto import (
    CapabilityEvolutionDTO,
)
from karsa.capability_engine.contracts.capability_timeseries_dto import (
    CapabilityTimeseriesDTO,
    CapabilityTimeseriesEntryDTO,
)
from karsa.capability_engine.contracts.governance_status_dto import (
    GovernanceStatusDTO,
)
from karsa.capability_engine.contracts.get_capability_health import (
    GetCapabilityHealthQuery,
)
from karsa.capability_engine.contracts.get_capability_evolution_history import (
    GetCapabilityEvolutionHistoryQuery,
)
from karsa.capability_engine.contracts.get_capability_score_timeseries import (
    GetCapabilityScoreTimeseriesQuery,
)
from karsa.capability_engine.contracts.get_capability_governance_status import (
    GetCapabilityGovernanceStatusQuery,
)
from karsa.capability_engine.domain.aggregates.capability_health_score import (
    CapabilityHealthScore,
)
from karsa.capability_engine.domain.value_objects.capability_score_component import (
    CapabilityScoreComponent,
)
from karsa.capability_engine.domain.value_objects.enums import (
    ScoreComponentName,
    EvolutionStatus,
)
from karsa.capability_engine.domain.value_objects.score_history_entry import (
    ScoreHistoryEntry,
)
from karsa.capability_engine.integration.capability_engine_bootstrap import (
    bootstrap,
)
from karsa.capability_engine.integration.capability_engine_fixture import (
    make_evolution,
    make_registry_entry,
)


@pytest.fixture
def ctx():
    return bootstrap()


@pytest.fixture
def facade(ctx):
    from karsa.capability_engine.integration.capability_query_facade import (
        CapabilityQueryFacade,
    )

    return CapabilityQueryFacade(
        health_projection_repo=ctx.health_projection_repo,
        evolution_projection_repo=ctx.evolution_projection_repo,
        timeseries_projection_repo=ctx.timeseries_projection_repo,
    )


class TestCapabilityHealthQuery:
    """Scenario 4: Health query -> DTO without projection internals."""

    def test_health_dto_returned(self, ctx, facade):
        # Setup: health score + projection rebuild
        ctx.health_score_repo.save(CapabilityHealthScore(
            health_score_id="qf-hs-001",
            capability_family_id="qf-family-001",
            current_score=0.75,
            score_components=[
                CapabilityScoreComponent(
                    component_name=ScoreComponentName.EXECUTION_QUALITY.value,
                    component_score=0.8, weight=0.25,
                    evaluation_count=1, confidence=0.9,
                ),
            ],
            evaluation_count=5,
            algorithm_version="v1.0",
        ))
        ctx.projection_service.rebuild_health_projection()

        query = GetCapabilityHealthQuery(
            capability_family_id="qf-family-001"
        )
        result = facade.get_health(query)

        assert result is not None
        assert isinstance(result, CapabilityHealthDTO)
        assert result.capability_family_id == "qf-family-001"
        assert result.current_score == 0.75
        assert result.evaluation_count == 5

    def test_health_returns_none_for_missing(self, facade):
        query = GetCapabilityHealthQuery(
            capability_family_id="nonexistent"
        )
        result = facade.get_health(query)
        assert result is None

    def test_health_dto_is_frozen(self, ctx, facade):
        ctx.health_score_repo.save(CapabilityHealthScore(
            health_score_id="qf-hs-002",
            capability_family_id="qf-family-002",
        ))
        ctx.projection_service.rebuild_health_projection()

        query = GetCapabilityHealthQuery(
            capability_family_id="qf-family-002"
        )
        result = facade.get_health(query)

        with pytest.raises(AttributeError):
            result.current_score = 0.9


class TestEvolutionHistoryQuery:
    """Scenario 5: Evolution history -> DTO with canonical filtering."""

    def test_evolution_dto_returned(self, ctx, facade):
        evo = make_evolution(
            capability_family_id="qf-family-003",
            evaluation_id="qf-eval-003",
        )
        ctx.evolution_repo.save(evo)
        ctx.version_registry.save(make_registry_entry(
            capability_family_id="qf-family-003",
            evaluation_id="qf-eval-003",
            evolution_id=evo.evolution_id,
        ))
        ctx.projection_service.rebuild_evolution_projection()

        query = GetCapabilityEvolutionHistoryQuery(
            capability_family_id="qf-family-003"
        )
        result = facade.get_evolution_history(query)

        assert result is not None
        assert isinstance(result, CapabilityEvolutionDTO)
        assert result.capability_family_id == "qf-family-003"
        assert result.total_evolutions == 1

    def test_evolution_returns_none_for_missing(self, facade):
        query = GetCapabilityEvolutionHistoryQuery(
            capability_family_id="nonexistent"
        )
        result = facade.get_evolution_history(query)
        assert result is None


class TestTimeseriesQuery:
    """Scenario 6: Timeseries -> DTO with version boundaries."""

    def test_timeseries_dto_returned(self, ctx, facade):
        ctx.health_score_repo.save(CapabilityHealthScore(
            health_score_id="qf-hs-004",
            capability_family_id="qf-family-004",
        ))
        ctx.score_history_repo.append(ScoreHistoryEntry(
            capability_family_id="qf-family-004",
            evaluation_id="qf-eval-004",
            evaluation_sequence=1,
            capability_version_id="qf-ver-001",
            score=0.6,
            algorithm_version="v1.0",
        ))
        ctx.projection_service.rebuild_timeseries_projection()

        query = GetCapabilityScoreTimeseriesQuery(
            capability_family_id="qf-family-004"
        )
        result = facade.get_timeseries(query)

        assert result is not None
        assert isinstance(result, CapabilityTimeseriesDTO)
        assert len(result.entries) == 1
        assert isinstance(result.entries[0], CapabilityTimeseriesEntryDTO)

    def test_timeseries_version_filter(self, ctx, facade):
        ctx.health_score_repo.save(CapabilityHealthScore(
            health_score_id="qf-hs-005",
            capability_family_id="qf-family-005",
        ))
        ctx.score_history_repo.append(ScoreHistoryEntry(
            capability_family_id="qf-family-005",
            evaluation_id="qf-eval-005a",
            evaluation_sequence=1,
            capability_version_id="qf-ver-v1",
            score=0.5,
            algorithm_version="v1.0",
        ))
        ctx.score_history_repo.append(ScoreHistoryEntry(
            capability_family_id="qf-family-005",
            evaluation_id="qf-eval-005b",
            evaluation_sequence=2,
            capability_version_id="qf-ver-v2",
            score=0.7,
            algorithm_version="v2.0",
        ))
        ctx.projection_service.rebuild_timeseries_projection()

        query = GetCapabilityScoreTimeseriesQuery(
            capability_family_id="qf-family-005",
            capability_version_id="qf-ver-v2",
        )
        result = facade.get_timeseries(query)

        assert result is not None
        assert len(result.entries) == 1
        assert result.entries[0].capability_version_id == "qf-ver-v2"


class TestGovernanceStatusQuery:
    """Scenario 3: Governance status -> DTO."""

    def test_governance_dto_returned(self, ctx, facade):
        ctx.health_score_repo.save(CapabilityHealthScore(
            health_score_id="qf-hs-006",
            capability_family_id="qf-family-006",
            consecutive_low_scores=0,
            consecutive_high_scores=0,
        ))
        ctx.projection_service.rebuild_health_projection()

        query = GetCapabilityGovernanceStatusQuery(
            capability_family_id="qf-family-006"
        )
        result = facade.get_governance_status(query)

        assert result is not None
        assert isinstance(result, GovernanceStatusDTO)
        assert result.is_suspended is False
        assert result.lifecycle_state == "ACTIVE"

    def test_governance_suspended_state(self, ctx, facade):
        ctx.health_score_repo.save(CapabilityHealthScore(
            health_score_id="qf-hs-007",
            capability_family_id="qf-family-007",
            consecutive_low_scores=3,
            consecutive_high_scores=0,
        ))
        ctx.projection_service.rebuild_health_projection()

        query = GetCapabilityGovernanceStatusQuery(
            capability_family_id="qf-family-007"
        )
        result = facade.get_governance_status(query)

        assert result is not None
        assert result.is_suspended is True
        assert result.lifecycle_state == "SUSPENDED"
        assert result.suspension_reason is not None
