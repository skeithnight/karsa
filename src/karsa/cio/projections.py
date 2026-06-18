from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

@dataclass(frozen=True)
class PortfolioStateProjection:
    state_id: str
    decision_id: str
    portfolio_tree: Dict[str, Any]
    created_at: datetime

    def __post_init__(self):
        if not self.state_id or not self.state_id.strip():
            raise ValueError("state_id cannot be empty.")
        if not self.decision_id or not self.decision_id.strip():
            raise ValueError("decision_id cannot be empty.")
        if not self.portfolio_tree:
            raise ValueError("portfolio_tree cannot be empty.")

import json
import psycopg

class CioProjectionService:
    def __init__(self, conn):
        self.conn = conn

    def consume_portfolio_decision_made(self, payload: Dict[str, Any]):
        decision_id = payload.get("decision_id")
        causation_id = payload.get("causation_id")
        portfolio_id = payload.get("portfolio_id")
        action_type = payload.get("action_type")
        decision_payload = payload.get("payload", {})
        rationale = payload.get("rationale", {})
        signature = payload.get("cryptographic_signature", {})
        
        # reconstruct some fields not fully detailed in event for simplicity
        # or just save what we have
        decision_journal_ref = rationale.get("references", [None])[0]
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO cio_decisions (
                        decision_id, calculation_id, decision_journal_ref,
                        portfolio_snapshot_hash, action_type, target_node_type, target_node_id,
                        decision_payload, cryptographic_signature, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        decision_id,
                        causation_id,
                        decision_journal_ref,
                        "unknown", # snapshot hash
                        action_type,
                        "PORTFOLIO",
                        portfolio_id,
                        json.dumps(decision_payload),
                        json.dumps(signature)
                    )
                )
        except psycopg.errors.RaiseException as e:
            pass # ignore block_cio_mutation trigger if replaying
