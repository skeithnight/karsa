from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime
from karsa.firm_intelligence.application.query_service import FirmIntelligenceQueryService
from karsa.firm_intelligence.api.dtos import IntelligenceResponseDTO

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])

# In a real app, Depends would inject the instantiated service
def get_query_service() -> FirmIntelligenceQueryService:
    pass # Dependency injection placeholder

@router.get("/cio/allocation-readiness", response_model=IntelligenceResponseDTO)
def get_allocation_readiness(
    regime_type: Optional[str] = None,
    date_target: Optional[datetime] = Query(None, description="Point in time reconstruction date"),
    service: FirmIntelligenceQueryService = Depends(get_query_service)
):
    return service.query_allocation_readiness(date_target)

@router.get("/governance/suspensions", response_model=IntelligenceResponseDTO)
def get_suspensions(
    since: Optional[datetime] = None,
    service: FirmIntelligenceQueryService = Depends(get_query_service)
):
    return service.query_governance_suspensions(since)

@router.get("/swarms/{urn}/diagnostics", response_model=IntelligenceResponseDTO)
def get_swarm_diagnostics(
    urn: str,
    service: FirmIntelligenceQueryService = Depends(get_query_service)
):
    return service.query_swarm_diagnostics(urn)
