from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

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
