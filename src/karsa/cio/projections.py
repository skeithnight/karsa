from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

@dataclass(frozen=True)
class PortfolioStateProjection:
    state_id: str
    decision_id: str
    portfolio_tree: Dict[str, Any]
    created_at: datetime

    def __post_init__(self):
        if not self.state_id or not self.state_id.strip():
            raise ValueError("state_id cannot be empty.")
        if not self.decision_id or not self.decision_id.strip():
            raise ValueError("decision_id cannot be empty.")
        if not self.portfolio_tree:
            raise ValueError("portfolio_tree cannot be empty.")
