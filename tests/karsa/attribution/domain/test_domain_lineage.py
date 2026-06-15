from datetime import datetime
from karsa.attribution.domain.model.lineage import RecomputationLineage

def test_recomputation_lineage_creation():
    lin = RecomputationLineage(
        session_id="session-2",
        superseded_session_id="session-1",
        recomputation_timestamp=datetime.utcnow()
    )
    assert lin.session_id == "session-2"
    assert lin.superseded_session_id == "session-1"

def test_reconstruct_lineage_chain():
    from karsa.attribution.domain.model.lineage import reconstruct_lineage_chain
    
    class DummyRecord:
        def __init__(self, attribution_version, superseded_by_version=None, invalidated_by_version=None):
            self.attribution_version = attribution_version
            self.superseded_by_version = superseded_by_version
            self.invalidated_by_version = invalidated_by_version

    assert reconstruct_lineage_chain([]) == ""

    assert reconstruct_lineage_chain([DummyRecord(1)]) == "Version 1"

    records = [
        DummyRecord(1, superseded_by_version=2),
        DummyRecord(2, invalidated_by_version=3),
        DummyRecord(3)
    ]
    expected = "Version 1\n\u2192 superseded by Version 2\n\u2192 invalidated by Version 3"
    assert reconstruct_lineage_chain(records) == expected

