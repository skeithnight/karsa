"""GetCapabilityHealthQuery -- Sprint-11. Wave-8.

Query contract for capability health data.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GetCapabilityHealthQuery:
    """Query for a single capability's health state."""

    capability_family_id: str
