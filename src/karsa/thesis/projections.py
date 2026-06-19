import logging
from typing import Any

logger = logging.getLogger(__name__)

class ThesisProjectionService:
    def __init__(self, conn: Any):
        self.conn = conn

    def handle_thesis_proposed(self, event_dict: dict):
        c = self.conn.cursor()
        payload = event_dict.get("payload", event_dict)
        stream_version = event_dict.get("stream_version", payload.get("stream_version", 1))
        
        snapshot_urn = payload.get("snapshot_urn")
        thesis_urn = payload.get("thesis_urn", "")
        title = payload.get("title", "")
        summary = payload.get("summary", "")
        rationale = payload.get("rationale", "")
        confidence = payload.get("confidence", 0.0)
        author_urn = payload.get("author_urn", "")
        regime_urn = payload.get("regime_urn", "")
        assumptions = payload.get("assumptions", [])
        
        import json
        c.execute("""
            INSERT INTO thesis_snapshots (
                snapshot_urn, snapshot_version, lifecycle_state, 
                thesis_urn, title, summary, rationale, confidence, 
                author_urn, regime_urn, assumptions_jsonb,
                origin_regime_snapshot_urn, supersedes_snapshot_urn, invalidates_snapshot_urn
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (snapshot_urn) DO NOTHING
        """, (snapshot_urn, stream_version, "PROPOSED", 
              thesis_urn, title, summary, rationale, confidence,
              author_urn, regime_urn, json.dumps(assumptions),
              "", None, None))
        logger.info(f"Projected ThesisProposedEvent for snapshot {snapshot_urn}")

    def handle_thesis_activated(self, event_dict: dict):
        c = self.conn.cursor()
        payload = event_dict.get("payload", event_dict)
        stream_version = event_dict.get("stream_version", payload.get("stream_version", 1))
        snapshot_urn = payload.get("snapshot_urn")
        c.execute("""
            INSERT INTO thesis_snapshots (snapshot_urn, snapshot_version, lifecycle_state)
            VALUES (%s, %s, %s)
            ON CONFLICT (snapshot_urn) DO UPDATE SET lifecycle_state = EXCLUDED.lifecycle_state, snapshot_version = EXCLUDED.snapshot_version
        """, (snapshot_urn, stream_version, "ACTIVE"))
        logger.info(f"Projected ThesisActivatedEvent for snapshot {snapshot_urn}")
