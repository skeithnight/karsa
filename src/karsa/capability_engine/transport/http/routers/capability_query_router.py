"""Capability query router -- Sprint-12. Wave-3.

GET endpoints for Capability Engine read operations.
Delegates to CapabilityQueryFacade only. No business logic.
"""

from fastapi import APIRouter, Depends, HTTPException

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
from karsa.capability_engine.integration.capability_query_facade import (
    CapabilityQueryFacade,
)
from karsa.capability_engine.transport.http.responses.capability_health_response import (
    CapabilityHealthResponse,
)
from karsa.capability_engine.transport.http.responses.capability_evolution_response import (
    CapabilityEvolutionResponse,
)
from karsa.capability_engine.transport.http.responses.capability_timeseries_response import (
    CapabilityTimeseriesResponse,
    TimeseriesEntryResponse,
)
from karsa.capability_engine.transport.http.dependencies import (
    get_query_facade,
)
from karsa.capability_engine.transport.http.responses.governance_status_response import (
    GovernanceStatusResponse,
)

router = APIRouter(prefix="/capabilities", tags=["Capability Queries"])


@router.get(
    "/{family_id}/health",
    response_model=CapabilityHealthResponse,
    summary="Get capability health state",
)
def get_health(
    family_id: str,
    facade: CapabilityQueryFacade = Depends(get_query_facade),
) -> CapabilityHealthResponse:
    """Get capability health state.

    Maps to CapabilityQueryFacade.get_health().
    Returns 404 if capability not found.
    """
    query = GetCapabilityHealthQuery(capability_family_id=family_id)
    result = facade.get_health(query)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Capability {family_id} not found",
        )

    return CapabilityHealthResponse(
        capability_family_id=result.capability_family_id,
        current_score=result.current_score,
        algorithm_version=result.algorithm_version,
        execution_quality_score=result.execution_quality_score,
        attribution_alignment_score=result.attribution_alignment_score,
        review_sentiment_score=result.review_sentiment_score,
        regime_fitness_score=result.regime_fitness_score,
        evaluation_count=result.evaluation_count,
        data_completeness=result.data_completeness,
        score_trend=result.score_trend,
        lifecycle_state=result.lifecycle_state,
        consecutive_low_scores=result.consecutive_low_scores,
        consecutive_high_scores=result.consecutive_high_scores,
        last_evaluated_at=result.last_evaluated_at,
    )


@router.get(
    "/{family_id}/evolution",
    response_model=CapabilityEvolutionResponse,
    summary="Get capability evolution history",
)
def get_evolution(
    family_id: str,
    facade: CapabilityQueryFacade = Depends(get_query_facade),
) -> CapabilityEvolutionResponse:
    """Get capability evolution history.

    Maps to CapabilityQueryFacade.get_evolution_history().
    Returns 404 if capability not found.
    """
    query = GetCapabilityEvolutionHistoryQuery(
        capability_family_id=family_id
    )
    result = facade.get_evolution_history(query)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Capability {family_id} not found",
        )

    return CapabilityEvolutionResponse(
        capability_family_id=result.capability_family_id,
        evaluation_id=result.evaluation_id,
        capability_urn=result.capability_urn,
        total_evolutions=result.total_evolutions,
        trigger_type_breakdown=result.trigger_type_breakdown,
        positive_evolutions=result.positive_evolutions,
        negative_evolutions=result.negative_evolutions,
        avg_score_change_bps=result.avg_score_change_bps,
        last_score_change_bps=result.last_score_change_bps,
        last_evolution_type=result.last_evolution_type,
        last_evaluated_at=result.last_evaluated_at,
    )


@router.get(
    "/{family_id}/timeseries",
    response_model=CapabilityTimeseriesResponse,
    summary="Get capability score time series",
)
def get_timeseries(
    family_id: str,
    capability_version_id: str | None = None,
    facade: CapabilityQueryFacade = Depends(get_query_facade),
) -> CapabilityTimeseriesResponse:
    """Get capability score time series.

    Maps to CapabilityQueryFacade.get_timeseries().
    Optional capability_version_id query parameter for version filtering (ADR-137).
    Returns 404 if capability not found.
    """
    query = GetCapabilityScoreTimeseriesQuery(
        capability_family_id=family_id,
        capability_version_id=capability_version_id,
    )
    result = facade.get_timeseries(query)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Capability {family_id} not found",
        )

    entries = [
        TimeseriesEntryResponse(
            evaluation_sequence=e.evaluation_sequence,
            score=e.score,
            algorithm_version=e.algorithm_version,
            recorded_at=e.recorded_at,
            capability_version_id=e.capability_version_id,
        )
        for e in result.entries
    ]

    return CapabilityTimeseriesResponse(
        capability_family_id=result.capability_family_id,
        entries=entries,
    )


@router.get(
    "/{family_id}/governance",
    response_model=GovernanceStatusResponse,
    summary="Get capability governance status",
)
def get_governance(
    family_id: str,
    facade: CapabilityQueryFacade = Depends(get_query_facade),
) -> GovernanceStatusResponse:
    """Get capability governance status.

    Maps to CapabilityQueryFacade.get_governance_status().
    Returns 404 if capability not found.
    """
    query = GetCapabilityGovernanceStatusQuery(
        capability_family_id=family_id
    )
    result = facade.get_governance_status(query)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Capability {family_id} not found",
        )

    return GovernanceStatusResponse(
        capability_family_id=result.capability_family_id,
        status=result.lifecycle_state,
        consecutive_low_scores=result.consecutive_low_scores,
        consecutive_high_scores=result.consecutive_high_scores,
        suspension_threshold=result.suspension_threshold,
        unsuspension_threshold=result.unsuspension_threshold,
    )
