from fastapi import APIRouter, Depends, HTTPException
from typing import List
from karsa.thesis.intelligence.infrastructure.storage.postgres.postgres_repo import PostgresThesisIntelligenceRepository
from karsa.thesis.intelligence.api.dtos import (
    TimelineEventDto, ConfidencePointDto, AssumptionIntelligenceDto, ThesisHealthDto
)

# In a real app we'd inject the repo, for now we assume a dependency getter
def get_intelligence_repo():
    from karsa.bootstrap import engine # or wherever the engine is
    return PostgresThesisIntelligenceRepository(engine)

intelligence_router = APIRouter(prefix="/intelligence", tags=["intelligence"])

@intelligence_router.get("/theses/{urn}/timeline", response_model=List[TimelineEventDto])
def get_thesis_timeline(urn: str, repo: PostgresThesisIntelligenceRepository = Depends(get_intelligence_repo)):
    return repo.get_timeline(urn)

@intelligence_router.get("/theses/{urn}/confidence", response_model=List[ConfidencePointDto])
def get_thesis_confidence(urn: str, repo: PostgresThesisIntelligenceRepository = Depends(get_intelligence_repo)):
    return repo.get_confidence_history(urn)

@intelligence_router.get("/theses/{urn}/assumptions", response_model=List[AssumptionIntelligenceDto])
def get_thesis_assumptions(urn: str, repo: PostgresThesisIntelligenceRepository = Depends(get_intelligence_repo)):
    return repo.get_assumptions(urn)

@intelligence_router.get("/theses/{urn}/health", response_model=ThesisHealthDto)
def get_thesis_health(urn: str, repo: PostgresThesisIntelligenceRepository = Depends(get_intelligence_repo)):
    health = repo.get_health(urn)
    if not health:
        raise HTTPException(status_code=404, detail="Health snapshot not found")
    return health
