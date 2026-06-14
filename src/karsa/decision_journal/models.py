from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from karsa.decision_journal.exceptions import ImmutabilityViolationException
from karsa.decision_journal.value_objects import DecisionContextSnapshot, DecisionEvidence

class ImmutableAggregate:
    """Base class for strictly immutable aggregates that prevent property modification at runtime."""
    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise ImmutabilityViolationException("Cannot modify property of an immutable aggregate.")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        raise ImmutabilityViolationException("Cannot delete property of an immutable aggregate.")

@dataclass
class DecisionJournalAggregate(ImmutableAggregate):
    decision_id: str
    proposing_agent_id: str
    signature: str
    thesis_urn: str
    context_snapshot: DecisionContextSnapshot
    created_at: datetime
    context_hash: Optional[str] = None
    context_uri: Optional[str] = None

@dataclass
class DecisionRevisionAggregate(ImmutableAggregate):
    revision_id: str
    parent_decision_id: str
    root_decision_id: str
    proposing_agent_id: str
    signature: str
    correction_reason: str
    context_snapshot: DecisionContextSnapshot
    created_at: datetime
    context_hash: Optional[str] = None
    context_uri: Optional[str] = None

@dataclass
class DecisionEvidenceAggregate(ImmutableAggregate):
    evidence_id: str
    decision_id: str
    attached_by_agent_id: str
    signature: str
    evidence: DecisionEvidence
    created_at: datetime
