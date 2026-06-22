"""Workers API routes -- stub."""

from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter(prefix="/workers", tags=["Workers"])


@router.get("/metrics")
def list_worker_metrics() -> Dict[str, Any]:
    """List worker metrics. Stub: returns empty."""
    return {"data": []}
