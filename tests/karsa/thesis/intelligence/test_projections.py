import pytest
from sqlalchemy import create_engine, text
from uuid import uuid4
from datetime import datetime, timezone
from karsa.thesis.intelligence.projections import ThesisIntelligenceProjectionService

@pytest.fixture
def db_connection():
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
        yield conn

def test_thesis_intelligence_projection_determinstic_math(db_connection):
    service = ThesisIntelligenceProjectionService()
    
    thesis_urn = "urn:karsa:thesis:1"
    
    # Event 1: Proposed
    e1 = {
        "event_type": "ThesisProposedEvent",
        "event_id": str(uuid4()),
        "stream_version": 1,
        "timestamp": datetime.now(timezone.utc),
        "payload": {
            "thesis_urn": thesis_urn,
            "confidence": 80.0,
            "state": "PROPOSED",
            "assumptions": [
                {"urn": "a1", "statement": "Macro grows", "is_valid": True},
                {"urn": "a2", "statement": "Micro shrinks", "is_valid": True}
            ]
        },
        "metadata": {
            "actor_urn": "urn:karsa:user:1",
            "rationale": "Initial proposal"
        }
    }
    service.handle(e1, db_connection)
    
    # Assert health score is 100% (2/2 valid)
    h1 = db_connection.execute(text("SELECT health_score, health_status FROM thesis_health_snapshots WHERE thesis_urn = 'urn:karsa:thesis:1'")).fetchone()
    assert h1[0] == 100.0
    assert h1[1] == 'GREEN'

    # Assert confidence history
    c1 = db_connection.execute(text("SELECT previous_confidence, new_confidence, delta FROM confidence_history WHERE stream_version = 1")).fetchone()
    assert c1[0] == 80.0
    assert c1[1] == 80.0
    assert c1[2] == 0.0
    
    # Event 2: Challenged
    e2 = {
        "event_type": "ThesisChallengedEvent",
        "event_id": str(uuid4()),
        "stream_version": 2,
        "timestamp": datetime.now(timezone.utc),
        "payload": {
            "thesis_urn": thesis_urn,
            "confidence": 40.0,
            "state": "CHALLENGED",
            "assumptions": [
                {"urn": "a1", "statement": "Macro grows", "is_valid": True},
                {"urn": "a2", "statement": "Micro shrinks", "is_valid": False}
            ]
        },
        "metadata": {
            "actor_urn": "urn:karsa:user:2",
            "rationale": "Micro is actually stable"
        }
    }
    service.handle(e2, db_connection)
    
    # Assert health score is 50% (1/2 valid) -> RED
    h2 = db_connection.execute(text("SELECT health_score, health_status FROM thesis_health_snapshots WHERE thesis_urn = 'urn:karsa:thesis:1'")).fetchone()
    assert h2[0] == 50.0
    assert h2[1] == 'YELLOW' # wait, 50 >= 50 is YELLOW.
    
    # Assert confidence history
    c2 = db_connection.execute(text("SELECT previous_confidence, new_confidence, delta FROM confidence_history WHERE stream_version = 2")).fetchone()
    assert c2[0] == 80.0
    assert c2[1] == 40.0
    assert c2[2] == -40.0
    
    # Assert assumption timeline and snapshot
    a2 = db_connection.execute(text("SELECT challenge_count FROM assumption_snapshots WHERE assumption_urn = 'a2'")).fetchone()
    assert a2[0] == 1
    
    # Idempotency check
    service.handle(e2, db_connection)
    a2_idem = db_connection.execute(text("SELECT challenge_count FROM assumption_snapshots WHERE assumption_urn = 'a2'")).fetchone()
    assert a2_idem[0] == 1 # count should not increase on idempotent replay
