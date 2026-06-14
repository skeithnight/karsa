from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional
import math

from karsa.post_mortem.exceptions import (
    AttributionWeightException,
    RecommendationStateConflictException,
    ImmutabilityViolationException,
)
from karsa.post_mortem.value_objects import (
    IncidentReference,
    FailureClassification,
    RootCauseContribution,
    PostMortemFinding,
)

class ImmutableAggregate:
    """Base class for strictly immutable aggregates that prevent property modification at runtime."""
    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise ImmutabilityViolationException("Cannot modify property of an immutable aggregate.")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        raise ImmutabilityViolationException("Cannot delete property of an immutable aggregate.")

@dataclass
class PostMortemRecord(ImmutableAggregate):
    postmortem_id: str
    incident_ref: IncidentReference
    failure_classification: FailureClassification
    root_causes: List[RootCauseContribution]
    findings: PostMortemFinding
    created_at: datetime

    def __post_init__(self):
        if not self.postmortem_id or not self.postmortem_id.strip():
            raise ValueError("postmortem_id cannot be empty.")
        if not isinstance(self.incident_ref, IncidentReference):
            raise ValueError("incident_ref must be an instance of IncidentReference.")
        if not isinstance(self.failure_classification, FailureClassification):
            raise ValueError("failure_classification must be an instance of FailureClassification.")
        if not isinstance(self.root_causes, list) or not all(isinstance(rc, RootCauseContribution) for rc in self.root_causes):
            raise ValueError("root_causes must be a list of RootCauseContribution.")
        if not isinstance(self.findings, PostMortemFinding):
            raise ValueError("findings must be an instance of PostMortemFinding.")
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be an instance of datetime.")

        # Invariant check: sum(all weights) == 1.0
        total_weight = sum(rc.weight for rc in self.root_causes)
        if not math.isclose(total_weight, 1.0, rel_tol=1e-9):
            raise AttributionWeightException(f"Root cause contribution weights must sum to exactly 1.0 (got {total_weight}).")

@dataclass
class Recommendation:
    recommendation_id: str
    postmortem_id: str
    target_context: str
    action_item: str
    parameters: Dict[str, Any]
    state: str  # PROPOSED, ACCEPTED, REJECTED, IMPLEMENTED, EXPIRED
    version: int
    updated_at: datetime

    def __post_init__(self):
        if not self.recommendation_id or not self.recommendation_id.strip():
            raise ValueError("recommendation_id cannot be empty.")
        if not self.postmortem_id or not self.postmortem_id.strip():
            raise ValueError("postmortem_id cannot be empty.")
        if not self.target_context or not self.target_context.strip():
            raise ValueError("target_context cannot be empty.")
        if not self.action_item or not self.action_item.strip():
            raise ValueError("action_item cannot be empty.")
        if self.parameters is None:
            raise ValueError("parameters cannot be None.")
        if self.state not in ("PROPOSED", "ACCEPTED", "REJECTED", "IMPLEMENTED", "EXPIRED"):
            raise ValueError(f"Invalid recommendation state: {self.state}")
        if not isinstance(self.version, int) or self.version < 1:
            raise ValueError("version must be a positive integer.")
        if not isinstance(self.updated_at, datetime):
            raise ValueError("updated_at must be an instance of datetime.")

    def accept(self):
        if self.state != "PROPOSED":
            raise RecommendationStateConflictException(
                f"Cannot transition recommendation {self.recommendation_id} from {self.state} to ACCEPTED."
            )
        self.state = "ACCEPTED"
        self.version += 1
        self.updated_at = datetime.utcnow()

    def reject(self):
        if self.state != "PROPOSED":
            raise RecommendationStateConflictException(
                f"Cannot transition recommendation {self.recommendation_id} from {self.state} to REJECTED."
            )
        self.state = "REJECTED"
        self.version += 1
        self.updated_at = datetime.utcnow()

    def implement(self):
        if self.state != "ACCEPTED":
            raise RecommendationStateConflictException(
                f"Cannot transition recommendation {self.recommendation_id} from {self.state} to IMPLEMENTED."
            )
        self.state = "IMPLEMENTED"
        self.version += 1
        self.updated_at = datetime.utcnow()

    def expire(self):
        if self.state not in ("PROPOSED", "ACCEPTED"):
            raise RecommendationStateConflictException(
                f"Cannot transition recommendation {self.recommendation_id} from {self.state} to EXPIRED."
            )
        self.state = "EXPIRED"
        self.version += 1
        self.updated_at = datetime.utcnow()
