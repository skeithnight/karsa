"""Performance API routes -- attribution endpoints."""

from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter(prefix="/performance", tags=["Performance"])


@router.get("/attribution")
def get_performance_attribution(
    start_date: str = "",
    end_date: str = "",
) -> Dict[str, Any]:
    """Performance attribution breakdown.

    Returns attribution data for the specified date range.
    Stub: returns empty data structure matching frontend expectations.
    """
    return {
        "data": [],
    }
