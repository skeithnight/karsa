from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass(frozen=True)
class DecisionJournalCreatedEvent:
    event_id: str
    decision_id: str
    proposing_agent_id: str
    thesis_urn: str
    context_hash: str
    context_uri: str
    timestamp: datetime
    event_version: int = 1

@dataclass(frozen=True)
class DecisionRevisionCreatedEvent:
    event_id: str
    revision_id: str
    parent_decision_id: str
    root_decision_id: str
    proposing_agent_id: str
    context_hash: str
    context_uri: str
    timestamp: datetime
    event_version: int = 1

@dataclass(frozen=True)
class DecisionEvidenceAttachedEvent:
    event_id: str
    evidence_id: str
    decision_id: str
    attached_by_agent_id: str
    evidence_hash: str
    timestamp: datetime
    event_version: int = 1

@dataclass(frozen=True)
class DecisionCorrectionRecordedEvent:
    event_id: str
    decision_id: str
    correction_reason: str
    timestamp: datetime
    event_version: int = 1

@dataclass(frozen=True)
class DecisionJournalArchivedEvent:
    event_id: str
    decision_id: str
    archived_at: datetime
    event_version: int = 1
