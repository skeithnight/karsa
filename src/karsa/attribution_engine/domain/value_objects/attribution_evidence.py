"""AttributionEvidence value object — Sprint-09."""
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class AttributionEvidence:
    """Links contributions to specific data points."""
    source_type: str  # EVALUATION | DECISION | REGIME | MANUAL
    source_id: str
    data_points: Dict[str, Any]
    explanation: str
