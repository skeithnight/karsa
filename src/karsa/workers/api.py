"""Workers API routes -- backed by dim_worker table in PostgreSQL."""

import os
from typing import Any, Dict, List

import psycopg
from fastapi import APIRouter

router = APIRouter(prefix="/workers", tags=["Workers"])


def _get_pg_connection():
    """Get a PostgreSQL connection from environment."""
    url = os.environ.get(
        "POSTGRES_URL",
        "postgresql://karsa:karsa_password@localhost:5432/karsa_db",
    )
    return psycopg.connect(url)


@router.get("/metrics")
def list_worker_metrics() -> Dict[str, Any]:
    """List worker metrics from dim_worker table."""
    try:
        with _get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT dim_worker_id, worker_urn, subject_type,
                              effective_from, is_current
                       FROM dim_worker
                       WHERE is_current = true
                       ORDER BY dim_worker_id"""
                )
                rows = cur.fetchall()
                if rows:
                    data = []
                    for row in rows:
                        worker_urn = row[1] or ""
                        # Extract role from URN (e.g., urn:karsa:worker:analyst-fundamental -> analyst-fundamental)
                        role = worker_urn.split(":")[-1] if worker_urn else row[2]
                        data.append({
                            "analystId": worker_urn,
                            "role": role or "N/A",
                            "winRateDisplay": "N/A",
                            "trustScoreDisplay": "N/A",
                        })
                    return {"data": data}
    except Exception:
        pass

    # Fallback: empty
    return {"data": []}
