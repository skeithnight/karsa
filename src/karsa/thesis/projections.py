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
        
        thesis_urn = payload.get("thesis_urn", "")
        snapshot_urn = payload.get("snapshot_urn") or f"{thesis_urn}:snapshot:{stream_version}"
        title = payload.get("title", "")
        summary = payload.get("summary", "")
        rationale = payload.get("rationale", "")
        confidence = payload.get("confidence", 0.0)
        author_urn = payload.get("author_urn", "")
        regime_urn = payload.get("regime_urn", "")
        assumptions = payload.get("assumptions", [])
        
        import json
        import psycopg
        try:
            with self.conn.transaction():
                c.execute("""
                    INSERT INTO theses (thesis_urn, current_snapshot_urn, current_status, aggregate_version)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (thesis_urn) DO NOTHING
                """, (thesis_urn, snapshot_urn, "PROPOSED", stream_version))
                
                c.execute("""
                    INSERT INTO thesis_snapshots (
                        snapshot_urn, snapshot_version, lifecycle_state, snapshot_state,
                        thesis_urn, title, summary, rationale, confidence, 
                        author_urn, regime_urn, assumptions_jsonb,
                        origin_regime_snapshot_urn, supersedes_snapshot_urn, invalidates_snapshot_urn,
                        thesis_manifest_hash, evidence_manifest_hash, assumption_manifest_hash
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (snapshot_urn, stream_version, "PROPOSED", "ACTIVE",
                      thesis_urn, title, summary, rationale, confidence,
                      author_urn, regime_urn, json.dumps(assumptions),
                      "", None, None, "", "", ""))
        except psycopg.errors.UniqueViolation:
            pass # Idempotent
        logger.info(f"Projected ThesisProposedEvent for snapshot {snapshot_urn}")

    def handle_thesis_activated(self, event_dict: dict):
        c = self.conn.cursor()
        payload = event_dict.get("payload", event_dict)
        stream_version = event_dict.get("stream_version", payload.get("stream_version", 1))
        snapshot_urn = payload.get("snapshot_urn")
        
        c.execute("""
            UPDATE thesis_snapshots 
            SET lifecycle_state = %s, snapshot_version = %s
            WHERE snapshot_urn = %s
        """, ("ACTIVE", stream_version, snapshot_urn))
        logger.info(f"Projected ThesisActivatedEvent for snapshot {snapshot_urn}")
