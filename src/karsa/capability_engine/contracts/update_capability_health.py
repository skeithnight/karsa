"""UpdateCapabilityHealthCommand -- Sprint-11. Wave-8.

Command contract for updating capability health score.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class UpdateCapabilityHealthCommand:
    """Command to record a health score evaluation.

    Maps to ScoringCommand without exposing domain types.
    """

    capability_family_id: str
    evaluation_id: str
    evaluation_sequence: int
    capability_version_id: str
    score: float  # 0.0-1.0
    components: List[Dict[str, Any]]  # CapabilityScoreComponent as dicts
    algorithm_version: str = "v1.0"
    capability_urn: str = ""
