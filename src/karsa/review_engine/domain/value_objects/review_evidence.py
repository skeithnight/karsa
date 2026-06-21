"""ReviewEvidence value object — Sprint-10."""
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ReviewEvidence:
    """Evidence supporting a review finding."""
    source_type: str  # PERFORMANCE | ATTRIBUTION | REGIME | MANUAL
    source_id: str
    data_points: Dict[str, Any]
    explanation: str

    def __post_init__(self):
        if not self.source_type:
            raise ValueError("source_type required")
        if not self.source_id:
            raise ValueError("source_id required")
