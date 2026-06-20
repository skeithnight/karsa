import pytest
from sqlalchemy import create_engine, text
from karsa.thesis.intelligence.projections import ThesisIntelligenceProjectionService
import uuid
from datetime import datetime

def test_executable_replay_validation():
    # 1. Setup mock database
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE thesis_timeline (
                event_id TEXT PRIMARY KEY, thesis_urn TEXT, stream_version INTEGER, causation_id TEXT,
                correlation_id TEXT, actor_urn TEXT, rationale TEXT, event_type TEXT, timestamp DATETIME,
                UNIQUE(thesis_urn, stream_version)
            )
        """))
        conn.execute(text("""
            CREATE TABLE confidence_history (
                id TEXT PRIMARY KEY, thesis_urn TEXT, stream_version INTEGER, previous_confidence FLOAT,
                new_confidence FLOAT, delta FLOAT, rationale TEXT, event_type TEXT, causation_id TEXT, timestamp DATETIME,
                UNIQUE(thesis_urn, stream_version)
            )
        """))
        conn.execute(text("""
            CREATE TABLE assumption_snapshots (
                assumption_urn TEXT PRIMARY KEY, thesis_urn TEXT, statement TEXT, is_valid BOOLEAN, challenge_count INTEGER
            )
        """))
        conn.execute(text("""
            CREATE TABLE assumption_timeline (
                event_id TEXT PRIMARY KEY, assumption_urn TEXT, event_type TEXT, actor_urn TEXT, rationale TEXT, timestamp DATETIME,
                UNIQUE(assumption_urn, event_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE thesis_health_snapshots (
                thesis_urn TEXT PRIMARY KEY, lifecycle_state TEXT, confidence FLOAT, total_assumptions INTEGER,
                valid_assumptions INTEGER, challenged_assumptions INTEGER, invalid_assumptions INTEGER,
                health_score FLOAT, health_status TEXT, snapshot_version INTEGER
            )
        """))
    
    # 2. Replay Journal
    events = [
        {
            "event_type": "ThesisProposedEvent", "event_id": str(uuid.uuid4()), "stream_version": 1, "timestamp": datetime.utcnow(),
            "payload": {"thesis_urn": "urn:karsa:thesis:x", "confidence": 90.0, "state": "PROPOSED", "assumptions": [
                {"urn": "a1", "statement": "Macro is good", "is_valid": True}
            ]},
            "metadata": {"actor_urn": "alice", "rationale": "initial"}
        },
        {
            "event_type": "ThesisChallengedEvent", "event_id": str(uuid.uuid4()), "stream_version": 2, "timestamp": datetime.utcnow(),
            "payload": {"thesis_urn": "urn:karsa:thesis:x", "confidence": 40.0, "state": "CHALLENGED", "assumptions": [
                {"urn": "a1", "statement": "Macro is good", "is_valid": False}
            ]},
            "metadata": {"actor_urn": "bob", "rationale": "macro turned bad"}
        }
    ]

    service = ThesisIntelligenceProjectionService()
    
    with engine.begin() as conn:
        for e in events:
            service.handle(e, conn)
            
    # 3. Verify counts
    with engine.connect() as conn:
        tl_count = conn.execute(text("SELECT COUNT(*) FROM thesis_timeline")).scalar()
        assert tl_count == 2
        
        ch_count = conn.execute(text("SELECT COUNT(*) FROM confidence_history")).scalar()
        assert ch_count == 2
        
        atl_count = conn.execute(text("SELECT COUNT(*) FROM assumption_timeline")).scalar()
        assert atl_count == 2
        
    # 4. Truncate Intelligence Tables
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM thesis_timeline"))
        conn.execute(text("DELETE FROM confidence_history"))
        conn.execute(text("DELETE FROM assumption_snapshots"))
        conn.execute(text("DELETE FROM assumption_timeline"))
        conn.execute(text("DELETE FROM thesis_health_snapshots"))
        
    # 5. Replay Projection Worker again
    with engine.begin() as conn:
        for e in events:
            service.handle(e, conn)
            
    # 6. Verify deterministic outputs
    with engine.connect() as conn:
        tl_count2 = conn.execute(text("SELECT COUNT(*) FROM thesis_timeline")).scalar()
        assert tl_count2 == 2 # deterministic reconstruction
        
        h_score = conn.execute(text("SELECT health_score FROM thesis_health_snapshots WHERE thesis_urn = 'urn:karsa:thesis:x'")).scalar()
        assert h_score == 0.0 # 0/1 valid
        
        delta = conn.execute(text("SELECT delta FROM confidence_history WHERE stream_version = 2")).scalar()
        assert delta == -50.0 # 40 - 90
