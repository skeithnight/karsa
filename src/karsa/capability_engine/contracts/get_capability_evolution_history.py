"""GetCapabilityEvolutionHistoryQuery -- Sprint-11. Wave-8.

Query contract for capability evolution history.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GetCapabilityEvolutionHistoryQuery:
    """Query for a capability's evolution history.

    Returns canonical records only (ADR-133).
    """

    capability_family_id: str
