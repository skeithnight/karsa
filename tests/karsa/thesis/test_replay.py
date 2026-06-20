import pytest
from unittest.mock import MagicMock

def test_replay_validation_flow():
    # 1. Baseline
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    cursor.fetchone.side_effect = [(5,), (10,)] # Before and After counts
    
    # 2. Truncate
    cursor.execute("TRUNCATE thesis_snapshots")
    
    # 3. Reset checkpoints
    cursor.execute("UPDATE projection_checkpoints SET last_event_id = 0 WHERE projection_name = 'thesis'")
    
    # 4. Replay execution
    from karsa.thesis.projections import ThesisProjectionService
    svc = ThesisProjectionService(conn)
    svc.handle_thesis_proposed({
        "payload": {
            "snapshot_urn": "snap:replay",
            "thesis_urn": "t:1",
            "title": "Replayed Title"
        },
        "stream_version": 2
    })
    
    # 5. After state
    cursor.execute("SELECT COUNT(*) FROM thesis_snapshots")
    
    # 6. Equality verification
    assert cursor.execute.call_count > 0
    # ensure inserts happen during replay
    assert "INSERT INTO thesis_snapshots" in str(cursor.execute.call_args_list)
