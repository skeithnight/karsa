"""Performance API routes -- attribution and Brier score endpoints."""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import psycopg
from fastapi import APIRouter

router = APIRouter(prefix="/performance", tags=["Performance"])


def _get_pg_connection():
    """Get a PostgreSQL connection from environment."""
    url = os.environ.get(
        "POSTGRES_URL",
        "postgresql://karsa:karsa_password@localhost:5432/karsa_db",
    )
    return psycopg.connect(url)


@router.get("/attribution")
def get_performance_attribution(
    start_date: str = "",
    end_date: str = "",
) -> Dict[str, Any]:
    """Performance attribution breakdown from attribution_records table."""
    try:
        with _get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT attribution_id, target_urn, target_type,
                              total_realized_return_bps, total_expected_return_bps,
                              total_variance_bps, attribution_summary, created_at
                       FROM attribution_records
                       ORDER BY created_at DESC
                       LIMIT 20"""
                )
                rows = cur.fetchall()
                if rows:
                    data = []
                    for row in rows:
                        realized = row[3]
                        expected = row[4]
                        summary = row[6] or {}
                        data.append({
                            "dateDisplay": row[7].strftime("%Y-%m-%d") if row[7] else "N/A",
                            "selectionReturnDisplay": f"{(realized or 0) / 100:.2f}%",
                            "allocationReturnDisplay": f"{(expected or 0) / 100:.2f}%",
                        })
                    return {"data": data}
    except Exception:
        pass

    # Fallback: empty
    return {"data": []}


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
