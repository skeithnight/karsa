from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

@dataclass
class ReviewVerdictReachedEvent:
    event_id: str
    session_id: str
    session_type: str
    target_type: str
    target_id: str
    target_version: str
    regime_id: str
    correlation_ids: list
    verdict_id: str
    outcome_rating: str
    justification: str
    timestamp: datetime
    event_version: int = 1

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": "ReviewVerdictReachedEvent",
            "session_id": self.session_id,
            "session_type": self.session_type,
            "target": {
                "target_type": self.target_type,
                "target_id": self.target_id,
                "target_version": self.target_version
            },
            "regime_id": self.regime_id,
            "correlation_ids": self.correlation_ids,
            "verdict": {
                "verdict_id": self.verdict_id,
                "outcome_rating": self.outcome_rating,
                "justification": self.justification
            },
            "timestamp": self.timestamp.isoformat(),
            "event_version": self.event_version
        }


@dataclass
class FeedbackAppliedEvent:
    event_id: str
    feedback_id: str
    session_id: str
    target_type: str
    target_id: str
    target_version: str
    category: str
    suggested_action: str
    applied_at: datetime
    event_version: int = 1

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": "FeedbackAppliedEvent",
            "feedback_id": self.feedback_id,
            "session_id": self.session_id,
            "target": {
                "target_type": self.target_type,
                "target_id": self.target_id,
                "target_version": self.target_version
            },
            "category": self.category,
            "suggested_action": self.suggested_action,
            "applied_at": self.applied_at.isoformat(),
            "event_version": self.event_version
        }


@dataclass
class ResearchRecommendationProposedEvent:
    event_id: str
    feedback_id: str
    target_type: str
    target_id: str
    target_version: str
    action: str
    parameters: dict
    timestamp: datetime
    event_version: int = 1

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": "ResearchRecommendationProposedEvent",
            "feedback_id": self.feedback_id,
            "target": {
                "target_type": self.target_type,
                "target_id": self.target_id,
                "target_version": self.target_version
            },
            "action": self.action,
            "parameters": self.parameters,
            "timestamp": self.timestamp.isoformat(),
            "event_version": self.event_version
        }
