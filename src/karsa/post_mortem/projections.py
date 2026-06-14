from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class RecommendationSummaryProjection:
    recommendation_id: str
    postmortem_id: str
    target_context: str
    state: str
    updated_at: datetime

    def __post_init__(self):
        if not self.recommendation_id or not self.recommendation_id.strip():
            raise ValueError("recommendation_id cannot be empty.")
        if not self.postmortem_id or not self.postmortem_id.strip():
            raise ValueError("postmortem_id cannot be empty.")
        if not self.target_context or not self.target_context.strip():
            raise ValueError("target_context cannot be empty.")
        if not self.state or not self.state.strip():
            raise ValueError("state cannot be empty.")
