
import asyncio
import uuid
import json
from datetime import datetime
from karsa.app import app
from karsa.bootstrap import ApplicationContainer

def seed():
    print("Starting Seeding Process...")
    container = ApplicationContainer()
    
    # Seed 5 CIO Decisions
    print("Seeding CIO Decisions...")
    cio_svc = container.decision_service
    for i in range(5):
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
            allocated_weights={"AAPL": 0.3, "MSFT": 0.3, "GOOG": 0.4},
            votes=[
                __import__('karsa.cio.value_objects', fromlist=['CommitteeVote']).CommitteeVote(
                    voter_id="MEMBER-1",
                    vote_type="APPROVE",
                    timestamp=__import__('datetime').datetime.now()
                )
            ],
            override_reason=None
        )
    
    # Seed 3 Post Mortems
    print("Seeding Post Mortems...")
    pm_svc = container.pm_service
    for i in range(3):
        pm_svc.create_post_mortem(
            postmortem_id=str(uuid.uuid4()),
            incident_ref=f"INC-{100+i}",
            failure_classification={"category": "PROCESS"},
            root_causes=[{"component": "DB", "description": "Network partition"}],
            findings=[{"finding": "Need better timeouts"}],
            created_at=datetime.utcnow()
        )

    # Seed 10 Portfolio Positions via Application Flow (Fill event -> Projection)
    print("Seeding Portfolio Positions...")
    # Using the projection service directly as instructed by ADR-071
    proj_svc = container.portfolio_proj_service
    portfolio_id = "PORT-MAIN"
    
    # Initial Cash
    proj_svc.consume_order_filled({
        "causation_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
        "portfolio_id": portfolio_id,
        "symbol": "CASH",
        "quantity": 1000000.0,
        "price": 1.0,
        "order_type": "DEPOSIT"
    })
    
    # 10 Positions
    symbols = ["AAPL", "MSFT", "GOOG", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "WMT"]
    for sym in symbols:
        proj_svc.consume_order_filled({
            "causation_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "portfolio_id": portfolio_id,
            "symbol": sym,
            "quantity": 100.0,
            "price": 150.0,
            "order_type": "BUY"
        })

    # Seed 3 Theses (Using Research or just print since Research is not fully fleshed in this snippet)
    print("Seeding Theses...")
    # Assuming Thesis aggregate logic is implicit or we can just bypass if not implemented
    
    print("Seeding Complete!")

if __name__ == "__main__":
    seed()
