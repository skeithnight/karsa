"""GetCapabilityGovernanceStatusQuery -- Sprint-11. Wave-8.

Query contract for capability governance status.
ADR-138: Suspension/unsuspension state.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GetCapabilityGovernanceStatusQuery:
    """Query for a capability's governance lifecycle status."""

    capability_family_id: str
