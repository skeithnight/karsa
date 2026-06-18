import logging
from typing import Any

logger = logging.getLogger(__name__)

class ThesisProjectionService:
    def __init__(self, conn: Any):
        self.conn = conn

    def handle_thesis_proposed(self, payload: dict):
        c = self.conn.cursor()
        snapshot_urn = payload.get("snapshot_urn")
        thesis_urn = payload.get("thesis_urn", "")
        # Assuming the payload has origin_regime_snapshot_urn etc. We default to ""
        c.execute("""
            INSERT INTO thesis_snapshots (snapshot_urn, snapshot_version, lifecycle_state, origin_regime_snapshot_urn, supersedes_snapshot_urn, invalidates_snapshot_urn)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (snapshot_urn) DO NOTHING
        """, (snapshot_urn, 1, "PROPOSED", "", None, None))
        logger.info(f"Projected ThesisProposedEvent for snapshot {snapshot_urn}")

    def handle_thesis_activated(self, payload: dict):
        c = self.conn.cursor()
        snapshot_urn = payload.get("snapshot_urn")
        c.execute("""
            INSERT INTO thesis_snapshots (snapshot_urn, snapshot_version, lifecycle_state, origin_regime_snapshot_urn, supersedes_snapshot_urn, invalidates_snapshot_urn)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (snapshot_urn) DO UPDATE SET lifecycle_state = EXCLUDED.lifecycle_state
        """, (snapshot_urn, 1, "ACTIVE", "", None, None))
        logger.info(f"Projected ThesisActivatedEvent for snapshot {snapshot_urn}")
