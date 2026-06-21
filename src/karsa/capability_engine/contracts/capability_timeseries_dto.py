"""CapabilityTimeseriesDTO -- Sprint-11. Wave-8.

Read-only contract for capability score time series.
ADR-137: Version boundaries preserved.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CapabilityTimeseriesEntryDTO:
    """Single entry in the score time series."""

    capability_family_id: str
    capability_version_id: str  # ADR-137
    evaluation_id: str
    evaluation_sequence: int  # ADR-136
    score: float  # 0.0-1.0
    algorithm_version: str  # ADR-134
    recorded_at: datetime


@dataclass(frozen=True)
class CapabilityTimeseriesDTO:
    """Public contract for a capability's score time series.

    Contains version-boundary-ordered entries.
    """

    capability_family_id: str
    entries: tuple  # Tuple[CapabilityTimeseriesEntryDTO, ...]
