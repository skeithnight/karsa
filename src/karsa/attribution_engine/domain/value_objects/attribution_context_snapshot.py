"""AttributionContextSnapshot value object — Sprint-09."""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AttributionContextSnapshot:
    """Immutable context for deterministic replay. ADR-097."""
    evaluation_snapshot: Dict[str, Any] = field(default_factory=dict)
    decision_snapshot: Dict[str, Any] = field(default_factory=dict)
    journal_snapshot: Optional[Dict[str, Any]] = None
    regime_snapshot: Optional[Dict[str, Any]] = None
    snapshot_hash: str = ""

    def validate(self) -> None:
        assert self.evaluation_snapshot, "evaluation_snapshot required"
        assert self.decision_snapshot, "decision_snapshot required"
        assert self.snapshot_hash, "snapshot_hash required"
