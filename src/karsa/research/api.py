"""Research API routes -- stub."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter

router = APIRouter(prefix="/research", tags=["Research"])


@router.get("/reports")
def list_research_reports(
    cursor: Optional[str] = None,
    limit: int = 50,
    ticker: Optional[str] = None,
    analyst: Optional[str] = None,
) -> Dict[str, Any]:
    """List research reports. Stub: returns empty."""
    return {"data": [], "next_cursor": None}
