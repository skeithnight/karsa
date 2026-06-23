"""Performance API routes -- attribution and Brier score endpoints."""

from datetime import datetime, timezone
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


@router.get("/brier-scores")
def get_brier_scores() -> List[Dict[str, Any]]:
    """Brier score timeseries for forecast calibration analysis.

    Returns an array of Brier score evaluation records ordered by sequence.
    Each entry contains the evaluation sequence, score value, algorithm
    version, and optional capability version reference.

    Stub: returns sample data to enable frontend development.
    """
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "evaluation_sequence": 1,
            "score": 0.25,
            "algorithm_version": "v1",
            "recorded_at": now,
            "capability_version_id": None,
        },
        {
            "evaluation_sequence": 2,
            "score": 0.18,
            "algorithm_version": "v1",
            "recorded_at": now,
            "capability_version_id": None,
        },
        {
            "evaluation_sequence": 3,
            "score": 0.12,
            "algorithm_version": "v2",
            "recorded_at": now,
            "capability_version_id": None,
        },
    ]
