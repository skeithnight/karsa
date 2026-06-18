
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
from karsa.thesis.infrastructure.storage.postgres.postgres_repo import PostgresThesisRepository
from karsa.thesis.domain.models import Thesis
from karsa.thesis.domain.value_objects import LifecycleState

def seed():
    print("Starting Seeding Process...")
    container = ApplicationContainer()
    
    # ---------------------------------------------------------
    # Seed 5 CIO Decisions (IDX Target Model)
    # ---------------------------------------------------------
    print("Seeding CIO Decisions...")
    cio_svc = container.decision_service
    decisions = [
        {"desc": "Increase BBCA allocation", "weights": {"BBCA.JK": 0.3, "BBRI.JK": 0.2, "BMRI.JK": 0.2, "TLKM.JK": 0.1, "ASII.JK": 0.2}},
        {"desc": "Reduce TLKM exposure", "weights": {"BBCA.JK": 0.3, "BBRI.JK": 0.2, "BMRI.JK": 0.2, "TLKM.JK": 0.05, "ASII.JK": 0.25}},
        {"desc": "Initiate ASII position", "weights": {"BBCA.JK": 0.3, "BBRI.JK": 0.2, "BMRI.JK": 0.2, "TLKM.JK": 0.05, "ASII.JK": 0.25}},
        {"desc": "Increase cash allocation", "weights": {"BBCA.JK": 0.25, "BBRI.JK": 0.15, "BMRI.JK": 0.15, "TLKM.JK": 0.05, "ASII.JK": 0.2, "CASH": 0.2}},
        {"desc": "Rebalance banking sector", "weights": {"BBCA.JK": 0.2, "BBRI.JK": 0.2, "BMRI.JK": 0.2, "TLKM.JK": 0.05, "ASII.JK": 0.2, "CASH": 0.15}}
    ]

    for i, dec in enumerate(decisions):
        decision_id = str(uuid.uuid4())
        cio_svc.create_decision(
            decision_id=decision_id,
            calculation_id=None,
            governance_exception_id=None,
            decision_journal_ref=f"JRN-CIO-{i}-{uuid.uuid4().hex[:8]}",
            portfolio_snapshot_hash="hash_xyz",
            action_type="APPROVE_ALLOCATION",
            target_node_type="PORTFOLIO",
            target_node_id="PORT-MAIN",
            allocated_weights=dec["weights"],
            votes=[
                __import__('karsa.cio.value_objects', fromlist=['CommitteeVote']).CommitteeVote(
                    voter_id="MEMBER-1",
                    vote_type="APPROVE",
                    timestamp=datetime.now(timezone.utc)
                )
            ],
            override_reason=None
        )
    
    # ---------------------------------------------------------
    # Seed 3 Post Mortems
    # ---------------------------------------------------------
    print("Seeding Post Mortems...")
    pm_svc = container.pm_service
    for i in range(3):
        pm_svc.create_post_mortem(
            postmortem_id=str(uuid.uuid4()),
            incident_ref=IncidentReference(incident_ref=f"urn:karsa:incident:seed:inc-{100+i}-{uuid.uuid4().hex[:8]}"),
            failure_classification=FailureClassification(failure_type="PROCESS", severity="HIGH", taxonomy_version=1),
            root_causes=[RootCauseContribution(cause_category="UNKNOWN", weight=1.0, description="Network partition")],
            findings=PostMortemFinding(timeline_events=[], evidence_uris=[]),
            created_at=datetime.now(timezone.utc)
        )

    # ---------------------------------------------------------
    # Seed Portfolio Positions via Application Flow
    # ---------------------------------------------------------
    print("Seeding Portfolio Positions...")
    proj_svc = container.portfolio_proj_service
    portfolio_id = "PORT-MAIN"
    
    # Initial Cash
    proj_svc.consume_order_filled({
        "causation_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
        "portfolio_id": portfolio_id,
        "symbol": "CASH",
        "quantity": 100000000.0,
        "price": 1.0,
        "order_type": "DEPOSIT"
    })
    
    # 5 IDX Positions
    symbols = ["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK"]
    for sym in symbols:
        proj_svc.consume_order_filled({
            "causation_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "portfolio_id": portfolio_id,
            "symbol": sym,
            "quantity": 10000.0,
            "price": 5000.0,
            "order_type": "BUY"
        })

    # ---------------------------------------------------------
    # Seed 3 Theses
    # ---------------------------------------------------------
    print("Seeding Theses via ThesisRepository...")
    thesis_repo = PostgresThesisRepository(container.conn)
    for i in range(3):
        t = Thesis(
            thesis_urn=f"urn:karsa:thesis:seed:th-{i}-{uuid.uuid4().hex[:8]}",
            current_snapshot_urn=f"urn:karsa:snapshot:seed:snap-{i}-{uuid.uuid4().hex[:8]}",
            current_status=LifecycleState.ACTIVE,
            aggregate_version=1
        )
        thesis_repo.save(t)
    
    print("Seed complete.")

if __name__ == "__main__":
    seed()
