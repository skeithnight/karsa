"""Allocation API routes — Sprint-06 Wave-7.

REST endpoints for allocation proposal workflow.
No business logic. Delegates to application services.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional

from karsa.allocation.api.dtos import (
    ProposalCreateRequest, ProposalResponse, ProposalListResponse,
    ProposalDetailResponse, ProposalApproveRequest, ProposalRejectRequest,
    ProposalModifyRequest, DecisionResponse,
)
from karsa.allocation.api.mappers import (
    map_proposal_to_response, map_proposal_to_list_item, map_proposal_to_detail,
)

router = APIRouter(prefix="/allocation", tags=["Capital Allocation"])


def get_recommendation_service():
    raise NotImplementedError("Dependency must be overridden in app bootstrap")


def get_decision_service():
    raise NotImplementedError("Dependency must be overridden in app bootstrap")


def get_projection_repo():
    raise NotImplementedError("Dependency must be overridden in app bootstrap")


@router.post("/proposals", status_code=status.HTTP_201_CREATED, response_model=ProposalResponse)
def generate_proposal(
    request: ProposalCreateRequest,
    service=Depends(get_recommendation_service),
    projection_repo=Depends(get_projection_repo),
):
    """Generates an allocation proposal from ranked workers."""
    try:
        # Get ranked workers from intelligence service
        ranked_workers = []
        if service.intelligence_query_service:
            intel_response = service.intelligence_query_service.query_allocation_readiness()
            ranked_workers = intel_response.data if hasattr(intel_response, 'data') else intel_response

        proposal = service.generate_proposal(
            total_capital=request.total_capital,
            ranked_workers=ranked_workers,
            policy_id=request.policy_id or "default-policy",
        )

        # Get status from projection
        proj = projection_repo.get_status(proposal.proposal_id)
        status_val = proj.status if proj else "PENDING"

        return map_proposal_to_response(proposal, status=status_val)

    except ValueError as e:
        detail = str(e)
        if "No allocatable workers" in detail:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/proposals", response_model=ProposalListResponse)
def list_proposals(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    service=Depends(get_recommendation_service),
    projection_repo=Depends(get_projection_repo),
):
    """Lists allocation proposals with optional status filter and pagination."""
    offset = (page - 1) * size

    if status_filter:
        projections = projection_repo.list_by_status(status_filter, limit=size, offset=offset)
        items = []
        for proj in projections:
            proposal = service.get_proposal(proj.proposal_id)
            if proposal:
                items.append(map_proposal_to_list_item(proposal, status=proj.status))
    else:
        proposals = service.list_proposals(limit=size, offset=offset)
        items = []
        for proposal in proposals:
            proj = projection_repo.get_status(proposal.proposal_id)
            status_val = proj.status if proj else "PENDING"
            items.append(map_proposal_to_list_item(proposal, status=status_val))

    return ProposalListResponse(
        data=items,
        pagination={"page": page, "size": size, "total_items": len(items)},
    )


@router.get("/proposals/{proposal_id}", response_model=ProposalDetailResponse)
def get_proposal(
    proposal_id: str,
    service=Depends(get_recommendation_service),
    projection_repo=Depends(get_projection_repo),
):
    """Retrieves a proposal by ID with status."""
    proposal = service.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Proposal {proposal_id} not found.")

    proj = projection_repo.get_status(proposal_id)
    return map_proposal_to_detail(proposal, projection=proj)
