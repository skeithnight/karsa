
import uuid
import json
from datetime import datetime, timezone
from karsa.bootstrap import ApplicationContainer
from karsa.post_mortem.value_objects import (
    IncidentReference,
    FailureClassification,
    RootCauseContribution,
    PostMortemFinding
)
from karsa.thesis.domain.models import Thesis
from karsa.thesis.domain.value_objects import LifecycleState
from karsa.shared.infrastructure.event_journal import EventJournalRepository
from karsa.shared.domain.event import DomainEvent

def seed():
    print("Starting Seeding Process...")
    container = ApplicationContainer()
    
    # ---------------------------------------------------------
    # Seed 5 CIO Decisions (IDX Target Model)
    # ---------------------------------------------------------
    print("Seeding CIO Decisions via Event Journal...")
    class PortfolioDecisionMadeEvent(DomainEvent):
        def __init__(self, decision_id, weights, desc):
            super().__init__()
            self.event_id = str(uuid.uuid4())
            self.stream_id = f"CIODecision-{decision_id}"
            self.aggregate_id = decision_id
            self.aggregate_type = "CIODecision"
            self.occurred_at = datetime.now(timezone.utc).isoformat()
            self.schema_version = 1
            self.correlation_id = decision_id
            self.causation_id = decision_id
            self.decision_id = decision_id
            self.portfolio_id = "PORT-MAIN"
            self.actor = {"actor_id": "cio-committee", "actor_type": "AGENT"}
            self.action_type = "APPROVE_ALLOCATION"
            self.payload = {"allocated_weights": weights, "votes": []}
            self.rationale = {"summary": desc, "references": []}
            self.cryptographic_signature = {"key_id": "seed", "algorithm": "Ed25519", "signature_hex": "seed"}
            self.timestamp = self.occurred_at
        def to_dict(self):
            return {k: v for k, v in self.__dict__.items() if k not in ['event_id', 'stream_id', 'aggregate_id', 'aggregate_type', 'occurred_at', 'schema_version']}

    decisions = [
        {"desc": "Increase BBCA allocation", "weights": {"BBCA.JK": 0.3, "BBRI.JK": 0.2, "BMRI.JK": 0.2, "TLKM.JK": 0.1, "ASII.JK": 0.2}},
        {"desc": "Reduce TLKM exposure", "weights": {"BBCA.JK": 0.3, "BBRI.JK": 0.2, "BMRI.JK": 0.2, "TLKM.JK": 0.05, "ASII.JK": 0.25}},
        {"desc": "Initiate ASII position", "weights": {"BBCA.JK": 0.3, "BBRI.JK": 0.2, "BMRI.JK": 0.2, "TLKM.JK": 0.05, "ASII.JK": 0.25}},
        {"desc": "Increase cash allocation", "weights": {"BBCA.JK": 0.25, "BBRI.JK": 0.15, "BMRI.JK": 0.15, "TLKM.JK": 0.05, "ASII.JK": 0.2, "CASH": 0.2}},
        {"desc": "Rebalance banking sector", "weights": {"BBCA.JK": 0.2, "BBRI.JK": 0.2, "BMRI.JK": 0.2, "TLKM.JK": 0.05, "ASII.JK": 0.2, "CASH": 0.15}}
    ]

    for i, dec in enumerate(decisions):
        decision_id = str(uuid.uuid4())
        event = PortfolioDecisionMadeEvent(decision_id, dec["weights"], dec["desc"])
        with container.pool.connection() as conn:
            EventJournalRepository(conn).append(event, 1)
            conn.commit()
    
    # ---------------------------------------------------------
    # Seed 3 Post Mortems
    # ---------------------------------------------------------
    print("Seeding Post Mortems via Event Journal...")
    class PostMortemRecordCreatedEvent(DomainEvent):
        def __init__(self, pm_id, inc_ref):
            super().__init__()
            self.event_id = str(uuid.uuid4())
            self.stream_id = f"PostMortem-{pm_id}"
            self.aggregate_id = pm_id
            self.aggregate_type = "PostMortem"
            self.occurred_at = datetime.now(timezone.utc).isoformat()
            self.schema_version = 1
            self.correlation_id = pm_id
            self.causation_id = pm_id
            self.postmortem_id = pm_id
            self.incident_ref = inc_ref
            self.failure_classification = {"failure_type": "PROCESS", "severity": "HIGH", "taxonomy_version": 1}
            self.root_causes = []
            self.findings = {"timeline_events": [], "evidence_uris": []}
            self.timestamp = self.occurred_at
        def to_dict(self):
            return {k: v for k, v in self.__dict__.items() if k not in ['event_id', 'stream_id', 'aggregate_id', 'aggregate_type', 'occurred_at', 'schema_version']}

    for i in range(3):
        pm_id = str(uuid.uuid4())
        inc_ref = f"urn:karsa:incident:seed:inc-{100+i}-{uuid.uuid4().hex[:8]}"
        event = PostMortemRecordCreatedEvent(pm_id, inc_ref)
        with container.pool.connection() as conn:
            EventJournalRepository(conn).append(event, 1)
            conn.commit()

    # ---------------------------------------------------------
    # Seed Portfolio Positions via Application Flow
    # ---------------------------------------------------------
    print("Seeding Portfolio Positions via Event Journal...")
    portfolio_id = "PORT-MAIN"
    
    class OrderFilledEvent(DomainEvent):
        def __init__(self, **kwargs):
            super().__init__()
            self.event_id = str(uuid.uuid4())
            self.stream_id = f"Portfolio-{portfolio_id}"
            self.aggregate_id = portfolio_id
            self.aggregate_type = "Portfolio"
            self.occurred_at = datetime.now(timezone.utc)
            self.schema_version = 1
            for k, v in kwargs.items():
                setattr(self, k, v)
        def to_dict(self):
            return {k: v for k, v in self.__dict__.items() if k not in ['event_id', 'stream_id', 'aggregate_id', 'aggregate_type', 'occurred_at', 'schema_version']}
    
    with container.pool.connection() as conn:
        journal_repo = EventJournalRepository(conn)
        
        journal_repo.append(OrderFilledEvent(
            causation_id=str(uuid.uuid4()), correlation_id=str(uuid.uuid4()), portfolio_id=portfolio_id, symbol="CASH", quantity=100000000.0, price=1.0, order_type="DEPOSIT", timestamp=datetime.now(timezone.utc).isoformat()
        ), 1)
        
        symbols = ["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK"]
        for idx, sym in enumerate(symbols):
            journal_repo.append(OrderFilledEvent(
                causation_id=str(uuid.uuid4()), correlation_id=str(uuid.uuid4()), portfolio_id=portfolio_id, symbol=sym, quantity=10000.0, price=5000.0, order_type="BUY", timestamp=datetime.now(timezone.utc).isoformat()
            ), idx + 2)
        conn.commit()

    # ---------------------------------------------------------
    # Seed 3 Theses
    # ---------------------------------------------------------
    print("Seeding Theses via EventJournalRepository...")
    class ThesisProposedEvent(DomainEvent):
        def __init__(self, urn):
            super().__init__()
            self.event_id = str(uuid.uuid4())
            self.stream_id = f"Thesis-{urn}"
            self.aggregate_id = urn
            self.aggregate_type = "Thesis"
            self.occurred_at = datetime.now(timezone.utc)
            self.schema_version = 1
            self.thesis_urn = urn
        def to_dict(self):
            return {"thesis_urn": self.thesis_urn}

    with container.pool.connection() as conn:
        journal_repo = EventJournalRepository(conn)
        for i in range(3):
            urn = f"urn:karsa:thesis:seed:th-{i}-{uuid.uuid4().hex[:8]}"
            journal_repo.append(ThesisProposedEvent(urn), 1)
        conn.commit()
    
    print("Seed complete.")

if __name__ == "__main__":
    seed()
