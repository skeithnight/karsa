from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class PortfolioDecisionProposed:
    """Event emitted when a new portfolio decision is proposed and awaits governance."""
    decision_payload: Dict[str, Any]
    context_snapshot: Dict[str, Any]
    originator_identity: Dict[str, str]

@dataclass
class PortfolioDecisionApproved:
    """Event emitted when a portfolio decision passes governance."""
    decision_id: str

@dataclass
class PortfolioTargetUpdated:
    """Event emitted when a portfolio's target is finally updated."""
    portfolio_id: str
    target_snapshot_id: str
