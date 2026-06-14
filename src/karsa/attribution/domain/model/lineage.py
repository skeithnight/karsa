from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class RecomputationLineage:
    """Tracks historical restatements and superseding chains for attribution audits."""
    session_id: str
    superseded_session_id: str
    recomputation_timestamp: datetime
