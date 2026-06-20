import pytest
from sqlalchemy import create_engine, text
from datetime import datetime
from karsa.firm_intelligence.projections import DataMartProjectionService

def test_intelligence_replay(db_engine, db_pool):
    # 1. Truncate DataMart
    with db_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE edge_swarm_attribution CASCADE"))
        conn.execute(text("TRUNCATE TABLE fact_alpha_generation CASCADE"))
        conn.execute(text("TRUNCATE TABLE fact_capability_transition CASCADE"))
        conn.execute(text("TRUNCATE TABLE dim_worker CASCADE"))
        conn.execute(text("TRUNCATE TABLE dim_regime CASCADE"))
        
    # 2. Simulate Projection Worker ingesting events
    proj_service = DataMartProjectionService()
    ts = datetime.utcnow()
    
    events = [
        {
            "event_type": "WorkerLifecycleTransitionedEvent",
            "global_sequence": 1,
            "created_at": ts,
            "payload": {
                "worker_urn": "urn:karsa:worker:1",
                "subject_type": "ANALYST",
                "old_state": "CANDIDATE",
                "new_state": "ACTIVE",
                "authority": "SYSTEM",
                "reason": "INITIAL"
            }
        },
        {
            "event_type": "WorkerAlphaRecordedEvent",
            "global_sequence": 2,
            "created_at": ts,
            "payload": {
                "worker_urn": "urn:karsa:worker:1",
                "regime_urn": "urn:karsa:regime:bull",
                "alpha_delta": 0.05,
                "cumulative_alpha": 0.05
            }
        },
        {
            "event_type": "CreditAllocatedEvent",
            "global_sequence": 3,
            "created_at": ts,
            "payload": {
                "parent_node_id": "urn:karsa:swarm:main",
                "subject_urn": "urn:karsa:worker:1",
                "attribution_urn": "urn:karsa:attr:1",
                "skill_ratio": 0.8
            }
        }
    ]
    
    with db_engine.begin() as conn:
        for ev in events:
            proj_service.handle(ev, conn)
            
    # 3. Verify
    with db_engine.connect() as conn:
        res = conn.execute(text("SELECT COUNT(*) FROM dim_worker")).fetchone()
        assert res[0] == 1 # One SCD2 record created
        
        res = conn.execute(text("SELECT COUNT(*) FROM fact_alpha_generation")).fetchone()
        assert res[0] == 1
        
        res = conn.execute(text("SELECT COUNT(*) FROM edge_swarm_attribution")).fetchone()
        assert res[0] == 1
        
    # 4. Replay Proof (Wipe and rebuild)
    with db_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dim_worker CASCADE"))
        conn.execute(text("TRUNCATE TABLE fact_alpha_generation CASCADE"))
        
    with db_engine.begin() as conn:
        for ev in events:
            proj_service.handle(ev, conn)
            
    with db_engine.connect() as conn:
        res = conn.execute(text("SELECT COUNT(*) FROM dim_worker")).fetchone()
        assert res[0] == 1 # Exact same count after replay
