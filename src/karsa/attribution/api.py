from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional

from karsa.attribution.infrastructure.repositories import (
    AttributionRepository,
    LineageGraphDTO,
    AssessmentDTO,
    FactDTO
)

router = APIRouter(prefix="/api/v1/attribution", tags=["Attribution V4.1"])

def get_attribution_repo() -> AttributionRepository:
    raise NotImplementedError("Dependency not wired")

@router.get("/lineages/{lineage_id}", response_model=LineageGraphDTO)
def get_lineage(
    lineage_id: str,
    repo: AttributionRepository = Depends(get_attribution_repo)
):
    result = repo.get_lineage(lineage_id)
    if not result:
        raise HTTPException(status_code=404, detail="Lineage not found")
    return result

@router.get("/assessments/{assessment_id}", response_model=AssessmentDTO)
def get_assessment(
    assessment_id: str,
    repo: AttributionRepository = Depends(get_attribution_repo)
):
    result = repo.get_assessment(assessment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return result

@router.get("/facts/{fact_id}", response_model=FactDTO)
def get_fact(
    fact_id: str,
    repo: AttributionRepository = Depends(get_attribution_repo)
):
    result = repo.get_fact(fact_id)
    if not result:
        raise HTTPException(status_code=404, detail="Fact not found")
    return result


@router.get("/brinson")
def get_brinson_attribution() -> List[Dict[str, Any]]:
    """Brinson attribution breakdown by period.

    Returns attribution data decomposed into selection, allocation,
    beta, and residual components with win rate and model accuracy.

    Stub: returns sample data to enable frontend development.
    """
    return [
        {
            "period": "MTD",
            "selection_pct": 1.2,
            "allocation_pct": 0.5,
            "beta_pct": 0.8,
            "residual_pct": -0.3,
            "total_return_pct": 2.2,
            "win_rate": 0.65,
            "model_accuracy": 0.72,
        },
        {
            "period": "YTD",
            "selection_pct": 3.8,
            "allocation_pct": 1.1,
            "beta_pct": 2.4,
            "residual_pct": -0.9,
            "total_return_pct": 6.4,
            "win_rate": 0.58,
            "model_accuracy": 0.68,
        },
    ]
