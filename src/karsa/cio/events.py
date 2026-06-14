from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass(frozen=True)
class PortfolioDecisionMadeEvent:
    event_id: str
    event_type: str
    correlation_id: str
    causation_id: str
    decision_id: str
    portfolio_id: str
    actor: Dict[str, Any]  # {"actor_id": "...", "actor_type": "HUMAN"|"AGENT"}
    action_type: str  # "APPROVE_ALLOCATION", "REJECT_ALLOCATION", "OVERRIDE"
    payload: Dict[str, Any]
    rationale: Dict[str, Any]  # {"summary": "...", "references": ["..."]}
    cryptographic_signature: Dict[str, Any]  # {"key_id": "...", "algorithm": "...", "signature_hex": "..."}
    timestamp: datetime
    event_version: int = 1

    def __post_init__(self):
        if not self.event_id or not self.event_id.strip():
            raise ValueError("event_id cannot be empty.")
        if not self.event_type or not self.event_type.strip():
            raise ValueError("event_type cannot be empty.")
        if not self.correlation_id or not self.correlation_id.strip():
            raise ValueError("correlation_id cannot be empty.")
        if not self.causation_id or not self.causation_id.strip():
            raise ValueError("causation_id cannot be empty.")
        if not self.decision_id or not self.decision_id.strip():
            raise ValueError("decision_id cannot be empty.")
        if not self.portfolio_id or not self.portfolio_id.strip():
            raise ValueError("portfolio_id cannot be empty.")
        if "actor_id" not in self.actor or "actor_type" not in self.actor:
            raise ValueError("actor must contain actor_id and actor_type.")
        if self.actor["actor_type"] not in ("HUMAN", "AGENT"):
            raise ValueError("actor_type must be either HUMAN or AGENT.")
        if not self.action_type or not self.action_type.strip():
            raise ValueError("action_type cannot be empty.")
        if "key_id" not in self.cryptographic_signature or "signature_hex" not in self.cryptographic_signature:
            raise ValueError("cryptographic_signature must contain key_id and signature_hex.")
