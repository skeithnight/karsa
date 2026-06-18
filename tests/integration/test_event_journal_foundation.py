import pytest
import uuid
import os
import json
from psycopg_pool import ConnectionPool
from datetime import datetime, timezone

@pytest.fixture(scope="module")
def db_conn():
    url = os.environ.get("POSTGRES_URL", "postgresql://karsa:karsa_password@127.0.0.1:5432/karsa_db")
    pool = ConnectionPool(url)
    with pool.connection() as conn:
        yield conn

def test_event_journal_foundation(db_conn):
    stream_id = f"stream-{uuid.uuid4()}"
    
    events = [
        (uuid.uuid4().hex, stream_id, 1, "TestA", json.dumps({"d": 1}), datetime.now(timezone.utc), "agg-1", "TestAgg", str(uuid.uuid4()), 1),
        (uuid.uuid4().hex, stream_id, 2, "TestB", json.dumps({"d": 2}), datetime.now(timezone.utc), "agg-1", "TestAgg", str(uuid.uuid4()), 1)
    ]
    
    # Insert
    for e in events:
        db_conn.execute(
            "INSERT INTO event_journal (id, stream_id, stream_version, event_type, payload, occurred_at, aggregate_id, aggregate_type, event_id, schema_version) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            e
        )
    db_conn.commit()
    
    # Read & Validate stream ordering
    cur = db_conn.execute("SELECT stream_version, event_type FROM event_journal WHERE stream_id = %s ORDER BY stream_version ASC", (stream_id,))
    rows = cur.fetchall()
    
    assert len(rows) == 2
    assert rows[0][0] == 1 and rows[0][1] == "TestA"
    assert rows[1][0] == 2 and rows[1][1] == "TestB"
    
    # Read & Validate global sequence replay ordering
    cur = db_conn.execute("SELECT sequence_id, event_type FROM event_journal WHERE stream_id = %s ORDER BY sequence_id ASC", (stream_id,))
    rows = cur.fetchall()
    
    assert rows[0][0] < rows[1][0]  # Sequence ID is monotonically increasing
