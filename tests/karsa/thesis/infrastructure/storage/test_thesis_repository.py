import pytest
from unittest.mock import MagicMock
from karsa.shared.domain.identity import OriginatorIdentity
from karsa.thesis.domain.model.thesis import Thesis
from karsa.thesis.domain.model.value_objects import (
    HypothesisStructure, ConfidenceModel, TimeHorizon, TimeClassification, ConfidenceSource
)
from karsa.thesis.infrastructure.storage.thesis_repository import PostgresThesisRepository
from karsa.shared.infrastructure.uow import ConcurrencyConflictError

def create_valid_thesis():
    originator = OriginatorIdentity("o1", "HUMAN", "v1")
    hypothesis = HypothesisStructure("H1", "Bull", "Bear", ["A1"], "Out", ["I1"], ["S1"])
    confidence = ConfidenceModel(0.8, None, ConfidenceSource.MANUAL, "2024")
    time_horizon = TimeHorizon("2024-01-01", "2024-12-31", TimeClassification.SHORT_TERM)
    return Thesis("t1", originator, hypothesis, confidence, time_horizon, [])

def test_save_new_thesis():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    
    repo = PostgresThesisRepository(conn)
    thesis = create_valid_thesis()
    
    repo.save(thesis)
    
    # Verify insert was called since version is 1
    assert "INSERT INTO thesis" in cursor.execute.call_args[0][0]

def test_occ_conflict():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    
    # Simulate update returning 0 rows
    cursor.rowcount = 0
    
    repo = PostgresThesisRepository(conn)
    thesis = create_valid_thesis()
    thesis.increment_version() # Now version 2, should trigger UPDATE
    
    with pytest.raises(ConcurrencyConflictError):
        repo.save(thesis)

def test_load_thesis():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    
    thesis = create_valid_thesis()
    from karsa.thesis.infrastructure.storage.thesis_mapper import ThesisMapper
    import json
    payload = json.dumps(ThesisMapper.to_payload(thesis))
    
    cursor.fetchone.return_value = ("t1", thesis.state.value, thesis.aggregate_version, payload, "2024", "2024")
    
    repo = PostgresThesisRepository(conn)
    loaded = repo.get_by_id("t1")
    
    assert loaded is not None
    assert loaded.identity.thesis_id == "t1"
    assert loaded.aggregate_version == 1
    assert loaded.state.value == "DRAFT"
