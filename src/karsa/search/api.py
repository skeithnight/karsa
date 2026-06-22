"""Search API routes -- stub."""

from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter(tags=["Search"])


@router.get("/search")
def search(q: str = "") -> Dict[str, Any]:
    """Global search. Stub: returns empty."""
    return {"results": []}
