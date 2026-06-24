"""Research API routes -- backed by theses table in PostgreSQL."""

import os
from typing import Any, Dict, List, Optional

import psycopg
from fastapi import APIRouter

router = APIRouter(prefix="/research", tags=["Research"])


def _get_pg_connection():
    """Get a PostgreSQL connection from environment."""
    url = os.environ.get(
        "POSTGRES_URL",
        "postgresql://karsa:karsa_password@localhost:5432/karsa_db",
    )
    return psycopg.connect(url)


@router.get("/reports")
def list_research_reports(
    cursor: Optional[str] = None,
    limit: int = 50,
    ticker: Optional[str] = None,
    analyst: Optional[str] = None,
) -> Dict[str, Any]:
    """List research reports from theses table."""
    try:
        with _get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT t.thesis_urn, t.current_status, t.aggregate_version,
                              t.created_at, s.title, s.confidence
                       FROM theses t
                       LEFT JOIN thesis_snapshots s ON s.thesis_urn = t.thesis_urn
                       ORDER BY t.created_at DESC
                       LIMIT %s""",
                    (limit,),
                )
                rows = cur.fetchall()
                if rows:
                    data = []
                    for row in rows:
                        created_at = row[3]
                        data.append({
                            "id": row[0],
                            "ticker": row[0].split(":")[-1] if row[0] else "N/A",
                            "analystId": "ai-researcher",
                            "conviction": row[5],
                            "publishedAtDisplay": created_at.strftime("%Y-%m-%d %H:%M") if created_at else "N/A",
                        })
                    return {"data": data, "next_cursor": None}
    except Exception:
        pass

    # Fallback: empty
    return {"data": [], "next_cursor": None}
