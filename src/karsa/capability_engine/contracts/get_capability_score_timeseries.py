"""GetCapabilityScoreTimeseriesQuery -- Sprint-11. Wave-8.

Query contract for capability score time series.
ADR-137: Version boundaries preserved.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GetCapabilityScoreTimeseriesQuery:
    """Query for a capability's score time series.

    ADR-137: Optional version filter.
    """

    capability_family_id: str
    capability_version_id: Optional[str] = None  # ADR-137
