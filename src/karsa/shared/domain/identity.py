from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class DecisionIdentity:
    """Canonical identity of a decision."""
    decision_id: str
    decision_fingerprint: str

@dataclass(frozen=True)
class OriginatorIdentity:
    """Canonical identity of the originator of a decision (human or model)."""
    originator_id: str
    originator_type: str  # e.g., 'HUMAN', 'LLM', 'QUANT'
    originator_version: str  # e.g., 'v1.2', '2024-05-snapshot'
    originator_worker_id: Optional[str] = None
    originator_model: Optional[str] = None
    originator_strategy: Optional[str] = None
