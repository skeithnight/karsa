from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass(frozen=True)
class IncidentReference:
    incident_ref: str

    def __post_init__(self):
        if not self.incident_ref or not self.incident_ref.strip():
            raise ValueError("incident_ref cannot be empty.")
        if not self.incident_ref.startswith("urn:karsa:incident:"):
            raise ValueError(f"incident_ref '{self.incident_ref}' must match format URN: 'urn:karsa:incident:<context>:<uuid>'")
        parts = self.incident_ref.split(":")
        if len(parts) < 5:
            raise ValueError(f"incident_ref '{self.incident_ref}' has invalid format. Expected URN: 'urn:karsa:incident:<context>:<uuid>'")

@dataclass(frozen=True)
class FailureClassification:
    failure_type: str
    severity: str
    taxonomy_version: int = 1

    def __post_init__(self):
        if not self.failure_type or not self.failure_type.strip():
            raise ValueError("failure_type cannot be empty.")
        if not self.severity or not self.severity.strip():
            raise ValueError("severity cannot be empty.")

@dataclass(frozen=True)
class RootCauseContribution:
    cause_category: str
    weight: float
    description: str

    def __post_init__(self):
        if not self.cause_category or not self.cause_category.strip():
            raise ValueError("cause_category cannot be empty.")
        if self.weight < 0.0 or self.weight > 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0. Got {self.weight}")
        if not self.description or not self.description.strip():
            raise ValueError("description cannot be empty.")

@dataclass(frozen=True)
class PostMortemFinding:
    timeline_events: List[Dict[str, Any]]
    evidence_uris: List[str]

    def __post_init__(self):
        if self.timeline_events is None:
            raise ValueError("timeline_events cannot be None.")
        if self.evidence_uris is None:
            raise ValueError("evidence_uris cannot be None.")

@dataclass(frozen=True)
class LessonLearned:
    action_item: str
    target_context: str
    parameters: Dict[str, Any]

    def __post_init__(self):
        if not self.action_item or not self.action_item.strip():
            raise ValueError("action_item cannot be empty.")
        if not self.target_context or not self.target_context.strip():
            raise ValueError("target_context cannot be empty.")
        if self.parameters is None:
            raise ValueError("parameters cannot be None.")
