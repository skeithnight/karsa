"""ReviewContextSnapshot value object — Sprint-10."""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ReviewContextSnapshot:
    """Immutable context for deterministic replay."""
    evaluation_snapshot: Dict[str, Any] = field(default_factory=dict)
    attribution_snapshot: Dict[str, Any] = field(default_factory=dict)
    decision_snapshot: Dict[str, Any] = field(default_factory=dict)
    journal_snapshot: Optional[Dict[str, Any]] = None
    regime_snapshot: Optional[Dict[str, Any]] = None
    snapshot_hash: str = ""

    def __post_init__(self):
        if not self.evaluation_snapshot:
            raise ValueError("evaluation_snapshot required")
        if not self.decision_snapshot:
            raise ValueError("decision_snapshot required")
        if not self.snapshot_hash:
            raise ValueError("snapshot_hash required")
