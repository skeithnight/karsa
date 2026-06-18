from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass(frozen=True)
class AttributionFact:
    """Immutable value object representing a factual dimension of attribution."""
    fact_id: str
    assessment_id: str
    dimensions: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self):
        if not self.fact_id:
            raise ValueError("fact_id is required")
        if not self.assessment_id:
            raise ValueError("assessment_id is required")
        if not isinstance(self.dimensions, dict):
            raise ValueError("dimensions must be a dictionary")
