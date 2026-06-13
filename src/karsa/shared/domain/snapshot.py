import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, List

@dataclass(frozen=True)
class DecisionContextSnapshot:
    """Immutable replay-grade snapshot of a decision context."""
    decision_context_id: str
    trigger_event_id: str
    trigger_event_type: str
    constraint_fingerprint: str
    optimizer_version: str
    engine_version: str
    git_hash: str
    created_at: str
    dependency_snapshot_ids: Dict[str, str]
    
    def generate_fingerprint(self) -> str:
        """Deterministically hash the snapshot for verification."""
        data = asdict(self)
        canonical_json = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
