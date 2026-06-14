from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List

@dataclass(frozen=True)
class PostMortemRecordCreatedEvent:
    event_id: str
    correlation_id: str
    causation_id: str
    timestamp: datetime
    postmortem_id: str
    incident_ref: str
    failure_classification: Dict[str, Any]
    root_causes: List[Dict[str, Any]]
    findings: Dict[str, Any]
    event_version: int = 1

@dataclass(frozen=True)
class RecommendationCreatedEvent:
    event_id: str
    correlation_id: str
    causation_id: str
    timestamp: datetime
    recommendation_id: str
    postmortem_id: str
    target_context: str
    action_item: str
    parameters: Dict[str, Any]
    event_version: int = 1

@dataclass(frozen=True)
class RecommendationAcceptedEvent:
    event_id: str
    correlation_id: str
    causation_id: str
    timestamp: datetime
    recommendation_id: str
    postmortem_id: str
    target_context: str
    event_version: int = 1

@dataclass(frozen=True)
class RecommendationRejectedEvent:
    event_id: str
    correlation_id: str
    causation_id: str
    timestamp: datetime
    recommendation_id: str
    postmortem_id: str
    target_context: str
    event_version: int = 1

@dataclass(frozen=True)
class RecommendationImplementedEvent:
    event_id: str
    correlation_id: str
    causation_id: str
    timestamp: datetime
    recommendation_id: str
    postmortem_id: str
    target_context: str
    event_version: int = 1

@dataclass(frozen=True)
class RecommendationExpiredEvent:
    event_id: str
    correlation_id: str
    causation_id: str
    timestamp: datetime
    recommendation_id: str
    postmortem_id: str
    target_context: str
    event_version: int = 1
