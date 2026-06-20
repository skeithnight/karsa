import time
import os
import uuid
from datetime import datetime
from karsa.bootstrap import get_postgres_pool
from karsa.cio.services import CIODecisionService
from karsa.cio.repositories import PostgresCIODecisionRepository
from karsa.cio.ports import DecisionJournalPort, GovernanceExceptionPort, EventPublisherPort
from cryptography.hazmat.primitives.asymmetric import ed25519
import json

class DummyDecisionJournalPort(DecisionJournalPort):
    def verify_journal_exists(self, ref: str) -> bool:
        return True
    def get_journal_expectations(self, journal_ref: str) -> dict:
        return {}

class DummyGovernanceExceptionPort(GovernanceExceptionPort):
    def verify_exception_token(self, exception_id: str, signature: str, payload: dict) -> bool:
        return True

class PostgresEventPublisherPort(EventPublisherPort):
    def __init__(self, pool):
        self.pool = pool

    def publish(self, event):
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                payload = {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "correlation_id": event.correlation_id,
                    "causation_id": event.causation_id,
                    "decision_id": event.decision_id,
                    "portfolio_id": event.portfolio_id,
                    "actor": event.actor,
                    "action_type": event.action_type,
                    "payload": event.payload,
                    "rationale": event.rationale,
                    "cryptographic_signature": event.cryptographic_signature,
                    "timestamp": event.timestamp.isoformat()
                }
                import uuid
                cur.execute(
                    """
                    INSERT INTO event_journal (
                        id, stream_id, stream_version, event_type, payload,
                        occurred_at, aggregate_id, aggregate_type, event_id
                    ) VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s, %s)
                    """,
                    (
                        uuid.uuid4().hex,
                        f"CIO-{event.decision_id}",
                        1,
                        event.event_type,
                        json.dumps(payload),
                        event.decision_id,
                        "CIODecisionAggregate",
                        event.event_id
                    )
                )

def main():
    print("Starting CIO Producer...")
    private_key = ed25519.Ed25519PrivateKey.generate()
    
    with get_postgres_pool() as pool:
        while True:
            try:
                with pool.connection() as conn:
                    decision_repo = PostgresCIODecisionRepository(conn)
                    journal_port = DummyDecisionJournalPort()
                    gov_port = DummyGovernanceExceptionPort()
                    event_pub = PostgresEventPublisherPort(pool)
                    
                    service = CIODecisionService(
                        decision_repo=decision_repo,
                        journal_port=journal_port,
                        governance_port=gov_port,
                        event_publisher=event_pub,
                        private_key=private_key
                    )
                    
                    decision_id = str(uuid.uuid4())
                    journal_ref = f"jrnl-{uuid.uuid4()}"
                    
                    print(f"Generating CIO Decision: {decision_id}")
                    
                    from karsa.cio.value_objects import OverrideReason
                    
                    service.create_decision(
                        decision_id=decision_id,
                        calculation_id=str(uuid.uuid4()),
                        governance_exception_id=None,
                        decision_journal_ref=journal_ref,
                        portfolio_snapshot_hash="hash",
                        action_type="OVERRIDE",
                        target_node_type="PORTFOLIO",
                        target_node_id="MAIN",
                        allocated_weights={"AAPL": 0.5, "MSFT": 0.5},
                        votes=[],
                        override_reason=OverrideReason(justification="Autonomous testing override", referenced_incident_urn="incident-123")
                    )
                    conn.commit() # Ensure repository changes are committed if any (none for now since we passed)
                time.sleep(30)
            except Exception as e:
                import sys
                print(f"Error in CIO Producer: {e}")
                sys.stdout.flush()
                time.sleep(5)

if __name__ == "__main__":
    main()
