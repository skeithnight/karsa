from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from karsa.decision_journal.domain.value_objects import (
    ConfidenceLevel, InvalidationCriteria, ExpectedOutcome, ExpectedHorizon, JournalHash
)

@dataclass(frozen=True)
class DecisionJournalEntry:
    journal_urn: str
    thesis_urn: str
    worker_urn: str
    strategy_urn: Optional[str]
    capability_urn: Optional[str]
    previous_journal_urn: Optional[str]
    journal_hash: JournalHash
    confidence: ConfidenceLevel
    rationale: str
    evidence_references: List[str]
    risk_assumptions: List[str]
    invalidation_criteria: InvalidationCriteria
    expected_outcome: ExpectedOutcome
    expected_horizon: ExpectedHorizon
    created_at: datetime
