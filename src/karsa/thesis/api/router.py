from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from .dtos import ThesisSummaryDto, ThesisDetailDto
import json

thesis_router = APIRouter()

def get_repo():
    from karsa.bootstrap import ApplicationContainer
    from karsa.thesis.infrastructure.storage.postgres.postgres_repo import PostgresThesisReadRepository
    return PostgresThesisReadRepository(ApplicationContainer().pool)

@thesis_router.get("/thesis", response_model=List[ThesisSummaryDto])
def list_theses(limit: int = Query(50), offset: int = Query(0), repo=Depends(get_repo)):
    return repo.get_all(limit, offset)

@thesis_router.get("/thesis/{urn}", response_model=ThesisDetailDto)
def get_thesis(urn: str, repo=Depends(get_repo)):
    res = repo.get_by_urn(urn)
    if not res:
        raise HTTPException(status_code=404, detail="Thesis not found")
    return res
