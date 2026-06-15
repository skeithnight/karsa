from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class PerformanceEvaluated:
    eval_urn: str
    outcome_urn: str
    created_at: datetime
