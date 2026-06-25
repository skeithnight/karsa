"""Search API routes -- queries event journal for decisions, theses, and tickers."""

import os
from typing import Any, Dict, List

import psycopg
from fastapi import APIRouter

router = APIRouter(tags=["Search"])


def _get_pg_connection():
    url = os.environ.get(
        "POSTGRES_URL",
        "postgresql://karsa:karsa_password@localhost:5432/karsa_db",
    )
    return psycopg.connect(url)


def _search_decisions(q: str) -> List[Dict[str, Any]]:
    try:
        conn = _get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT payload->>'decision_id', payload->>'ticker',
                       payload->>'action', payload->>'conviction',
                       payload->>'rationale', payload->>'entry_price',
                       payload->>'exit_target', payload->>'stop_loss',
                       payload->>'position_size_pct'
                FROM event_journal
                WHERE event_type = 'InvestmentDecisionCreatedEvent'
                AND (
                    LOWER(payload->>'ticker') LIKE LOWER(%s)
                    OR LOWER(payload->>'rationale') LIKE LOWER(%s)
                    OR LOWER(payload->>'action') LIKE LOWER(%s)
                )
                ORDER BY occurred_at DESC
                LIMIT 10
            """, (f"%{q}%", f"%{q}%", f"%{q}%"))
            rows = cur.fetchall()
        conn.close()
        return [{"type": "DECISION", "id": r[0] or "", "label": f"{r[1] or ''} {r[2] or ''} — {r[3] or ''}", "ticker": r[1] or "", "action": r[2] or "", "conviction": r[3] or "", "rationale": r[4] or "", "entry_price": r[5], "exit_target": r[6], "stop_loss": r[7], "position_size_pct": r[8], "route": "/signals"} for r in rows]
    except Exception:
        return []


def _search_theses(q: str) -> List[Dict[str, Any]]:
    try:
        conn = _get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT thesis_urn, title, summary, confidence, lifecycle_state
                FROM thesis_snapshots
                WHERE (LOWER(title) LIKE LOWER(%s) OR LOWER(summary) LIKE LOWER(%s) OR LOWER(thesis_urn) LIKE LOWER(%s))
                AND title IS NOT NULL AND title != ''
                ORDER BY created_at DESC LIMIT 10
            """, (f"%{q}%", f"%{q}%", f"%{q}%"))
            rows = cur.fetchall()
        conn.close()
        return [{"type": "THESIS", "id": r[0] or "", "label": f"{r[1]} (confidence: {r[3]})", "title": r[1] or "", "summary": r[2] or "", "confidence": float(r[3]) if r[3] else 0, "status": r[4] or "", "route": f"/theses/{r[0]}" if r[0] else "/theses"} for r in rows]
    except Exception:
        return []


def _search_tickers(q: str) -> List[Dict[str, Any]]:
    try:
        conn = _get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT asset_id FROM universe_members_table
                WHERE LOWER(asset_id) LIKE LOWER(%s)
                LIMIT 20
            """, (f"%{q}%",))
            rows = cur.fetchall()
        conn.close()
        return [{"type": "TICKER", "id": r[0], "label": r[0], "ticker": r[0], "route": f"/signals?ticker={r[0].replace('.JK','')}"} for r in rows]
    except Exception:
        return []


@router.get("/search")
def search(q: str = "") -> Dict[str, Any]:
    if not q or len(q.strip()) < 2:
        return {"results": []}
    results = _search_tickers(q) + _search_decisions(q) + _search_theses(q)
    return {"results": results[:20]}
