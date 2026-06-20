import pytest
from unittest.mock import MagicMock
from karsa.thesis.projections import ThesisProjectionService

def test_thesis_projection_idempotency():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    svc = ThesisProjectionService(mock_conn)
    svc.handle_thesis_proposed({
        "snapshot_urn": "snap:1",
        "thesis_urn": "thesis:1",
        "title": "Title",
        "assumptions": [{"urn": "a1", "statement": "S1"}]
    })
    
    assert mock_cursor.execute.call_count == 1
    # Check that INSERT uses ON CONFLICT DO NOTHING for Proposed
    sql = mock_cursor.execute.call_args[0][0]
    assert "ON CONFLICT (snapshot_urn) DO NOTHING" in sql
