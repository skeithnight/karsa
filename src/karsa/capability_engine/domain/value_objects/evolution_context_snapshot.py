"""Evolution context snapshot value object -- Sprint-11. ADR-135."""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, Optional


def _compute_snapshot_hash(data: Dict) -> str:
    """Compute SHA-256 hash of serialized snapshot data."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EvolutionContextSnapshot:
    """Immutable context captured at evolution write time for deterministic replay.

    Contains snapshots from upstream engines and the capability's own state.
    The snapshot_hash is a SHA-256 of the concatenated snapshot data.
    snapshot_source_versions tracks the checkpoint sequence of every source
    projection at capture time (ADR-135).
    """

    capability_snapshot: Dict  # required: current capability state
    review_snapshot: Optional[Dict] = None
    attribution_snapshot: Optional[Dict] = None
    execution_snapshot: Optional[Dict] = None
    snapshot_hash: str = ""  # SHA-256 of all snapshot data
    snapshot_source_versions: Dict = field(default_factory=dict)  # ADR-135

    def __post_init__(self) -> None:
        if not self.capability_snapshot:
            raise ValueError("capability_snapshot is required")
        if not any(
            [
                self.review_snapshot,
                self.attribution_snapshot,
                self.execution_snapshot,
            ]
        ):
            raise ValueError(
                "At least one of review_snapshot, attribution_snapshot, "
                "or execution_snapshot is required"
            )
        # Validate hash if provided, compute if empty
        if self.snapshot_hash:
            expected = self._compute_hash()
            if self.snapshot_hash != expected:
                raise ValueError(
                    f"snapshot_hash mismatch. Expected {expected}, "
                    f"got {self.snapshot_hash}"
                )

    def _compute_hash(self) -> str:
        """Compute the expected hash from snapshot data."""
        data = {
            "capability": self.capability_snapshot,
            "review": self.review_snapshot,
            "attribution": self.attribution_snapshot,
            "execution": self.execution_snapshot,
            "source_versions": self.snapshot_source_versions,
        }
        return _compute_snapshot_hash(data)

    def verify_hash(self) -> bool:
        """Verify that the stored hash matches the recomputed hash."""
        return self.snapshot_hash == self._compute_hash()
