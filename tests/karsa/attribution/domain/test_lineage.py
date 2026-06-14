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
