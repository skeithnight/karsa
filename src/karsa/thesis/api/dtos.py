from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ThesisSummaryDto(BaseModel):
    urn: str
    title: str
    status: str
    confidence: float
    version: int
    author_urn: str
    regime_urn: str
    last_updated: Optional[str] = None

class ThesisDetailDto(BaseModel):
    urn: str
    current_snapshot_urn: str
    title: str
    summary: str
    rationale: str
    confidence: float
    author_urn: str
    regime_urn: str
    status: str
    version: int
    assumptions: List[Dict[str, Any]]
