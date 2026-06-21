"""Capability command router -- Sprint-12. Wave-2.

POST endpoints for Capability Engine write operations.
Delegates to CommandFacade only. No business logic here.
"""

import uuid

from fastapi import APIRouter, Depends

from karsa.capability_engine.contracts.record_capability_evolution import (
    RecordCapabilityEvolutionCommand,
)
from karsa.capability_engine.contracts.update_capability_health import (
    UpdateCapabilityHealthCommand,
)
from karsa.capability_engine.contracts.rebuild_capability_projections import (
    RebuildCapabilityProjectionsCommand,
)
from karsa.capability_engine.contracts.reconcile_capability_state import (
    ReconcileCapabilityStateCommand,
)
from karsa.capability_engine.integration.capability_command_facade import (
    CapabilityCommandFacade,
)
from karsa.capability_engine.transport.http.requests.record_capability_evolution_request import (
    RecordCapabilityEvolutionRequest,
)
from karsa.capability_engine.transport.http.requests.update_capability_health_request import (
    UpdateCapabilityHealthRequest,
)
from karsa.capability_engine.transport.http.requests.rebuild_capability_projections_request import (
    RebuildCapabilityProjectionsRequest,
)
from karsa.capability_engine.transport.http.requests.reconcile_capability_state_request import (
    ReconcileCapabilityStateRequest,
)
from karsa.capability_engine.transport.http.dependencies import (
    get_command_facade,
)
from karsa.capability_engine.transport.http.responses.command_result_response import (
    CommandResultResponse,
)

router = APIRouter(prefix="/capabilities", tags=["Capability Commands"])


def _to_response(result, request_id: str | None = None) -> CommandResultResponse:
    """Map facade CommandResult to transport CommandResultResponse."""
    return CommandResultResponse(
        success=result.success,
        message=result.message,
        request_id=request_id,
        data=result.data,
    )


@router.post(
    "/evolutions",
    response_model=CommandResultResponse,
    status_code=201,
    summary="Record a capability evolution",
)
def record_evolution(
    request: RecordCapabilityEvolutionRequest,
    facade: CapabilityCommandFacade = Depends(get_command_facade),
) -> CommandResultResponse:
    """Record a capability evolution.

    Maps to CapabilityCommandFacade.record_evolution().
    """
    request_id = str(uuid.uuid4())

    command = RecordCapabilityEvolutionCommand(
        capability_family_id=request.capability_family_id,
        evaluation_id=request.evaluation_id,
        trigger_type=request.trigger_type.value,
        capability_version_id=request.capability_version_id,
        capability_urn=request.capability_urn,
        evolution_type=request.evolution_type.value,
        before_score=request.before_score,
        after_score=request.after_score,
        score_change_bps=request.score_change_bps,
        before_lifecycle_state=request.before_lifecycle_state,
        after_lifecycle_state=request.after_lifecycle_state,
        source_type=request.source_type,
        source_id=request.source_id,
        finding_ids=request.finding_ids,
        attribution_contribution_ids=request.attribution_contribution_ids,
        capability_snapshot=request.capability_snapshot,
        review_snapshot=request.review_snapshot,
        attribution_snapshot=request.attribution_snapshot,
        execution_snapshot=request.execution_snapshot,
        snapshot_source_versions=request.snapshot_source_versions,
        evaluation_sequence=request.evaluation_sequence,
        quality_score=request.quality_score,
        attribution_id=request.attribution_id,
        review_id=request.review_id,
        findings=request.findings,
        attribution_refs=request.attribution_refs,
    )

    result = facade.record_evolution(command)
    return _to_response(result, request_id)


@router.post(
    "/health",
    response_model=CommandResultResponse,
    status_code=200,
    summary="Update capability health score",
)
def update_health(
    request: UpdateCapabilityHealthRequest,
    facade: CapabilityCommandFacade = Depends(get_command_facade),
) -> CommandResultResponse:
    """Update a capability health score.

    Maps to CapabilityCommandFacade.update_health().
    """
    request_id = str(uuid.uuid4())

    components = [
        {
            "component_name": c.component_name,
            "component_score": c.component_score,
            "weight": c.weight,
            "evaluation_count": c.evaluation_count,
            "confidence": c.confidence,
        }
        for c in request.components
    ]

    command = UpdateCapabilityHealthCommand(
        capability_family_id=request.capability_family_id,
        evaluation_id=request.evaluation_id,
        evaluation_sequence=request.evaluation_sequence,
        capability_version_id=request.capability_version_id,
        score=request.score,
        components=components,
        algorithm_version=request.algorithm_version,
        capability_urn=request.capability_urn,
    )

    result = facade.update_health(command)
    return _to_response(result, request_id)


@router.post(
    "/projections/rebuild",
    response_model=CommandResultResponse,
    status_code=200,
    summary="Rebuild capability projections",
)
def rebuild_projections(
    request: RebuildCapabilityProjectionsRequest,
    facade: CapabilityCommandFacade = Depends(get_command_facade),
) -> CommandResultResponse:
    """Trigger projection rebuilds.

    Maps to CapabilityCommandFacade.rebuild_projections().
    ADR-135: Checkpoint validation supported.
    """
    request_id = str(uuid.uuid4())

    command = RebuildCapabilityProjectionsCommand(
        projection_name=request.projection_name,
        source_checkpoint=request.source_checkpoint,
        current_checkpoint=request.current_checkpoint,
    )

    result = facade.rebuild_projections(command)
    return _to_response(result, request_id)


@router.post(
    "/reconcile",
    response_model=CommandResultResponse,
    status_code=200,
    summary="Reconcile capability state",
)
def reconcile(
    request: ReconcileCapabilityStateRequest,
    facade: CapabilityCommandFacade = Depends(get_command_facade),
) -> CommandResultResponse:
    """Trigger state reconciliation.

    Maps to CapabilityCommandFacade.reconcile().
    ADR-130: Recovery path for split Transaction A/B.
    """
    request_id = str(uuid.uuid4())

    command = ReconcileCapabilityStateCommand(
        dry_run=request.dry_run,
    )

    result = facade.reconcile(command)
    return _to_response(result, request_id)
