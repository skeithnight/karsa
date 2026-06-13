from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import datetime

@dataclass(frozen=True)
class AttributionCalculatedPayload:
    attribution_id: str
    outcome_id: str
    source_context_id: str
    attribution_generation: int
    outcome_sequence: int
    policy_input_snapshot: Dict[str, Any]
    allocations: List[Dict[str, Any]]
    governance_audit_context: Optional[Dict[str, str]] = None
    parent_attribution_id: Optional[str] = None
    attribution_scope: str = "REALIZED_PNL"
    algorithm_hash: str = "hash_v1"
    
@dataclass(frozen=True)
class AttributionReversedPayload:
    attribution_id: str
    governance_audit_context: Dict[str, str]
    reason: str
