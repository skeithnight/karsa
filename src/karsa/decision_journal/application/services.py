from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from karsa.decision_journal.domain.models import DecisionJournalEntry
from karsa.decision_journal.domain.value_objects import (
    ConfidenceLevel, InvalidationCriteria, ExpectedOutcome, ExpectedHorizon, JournalHash
)
from karsa.decision_journal.domain.repository.repositories import DecisionJournalRepository
from karsa.decision_journal.domain.events import DecisionJournalAppended

@dataclass
class AppendDecisionJournalCommand:
    journal_urn: str
    thesis_urn: str
    worker_urn: str
    strategy_urn: Optional[str]
    capability_urn: Optional[str]
    confidence_value: str
    rationale: str
    evidence_references: List[str]
    risk_assumptions: List[str]
    invalidation_criteria_text: str
    expected_outcome_value: str
    expected_outcome_metric: str
    expected_horizon_days: int

class AppendDecisionJournalService:
    def __init__(self, repository: DecisionJournalRepository, event_bus):
        self.repository = repository
        self.event_bus = event_bus

    def execute(self, command: AppendDecisionJournalCommand) -> DecisionJournalEntry:
        from decimal import Decimal
        confidence = ConfidenceLevel(Decimal(command.confidence_value))
        invalidation = InvalidationCriteria(command.invalidation_criteria_text)
        outcome = ExpectedOutcome(Decimal(command.expected_outcome_value), command.expected_outcome_metric)
        horizon = ExpectedHorizon(command.expected_horizon_days)
        
        # Thesis-oriented journal evolution
        latest = self.repository.fetch_latest_by_thesis(command.thesis_urn)
        previous_urn = latest.journal_urn if latest else None
        previous_hash = latest.journal_hash.hash_value if latest else None
        
        jhash = JournalHash.generate(command.journal_urn, command.thesis_urn, previous_hash)
        
        entry = DecisionJournalEntry(
            journal_urn=command.journal_urn,
            thesis_urn=command.thesis_urn,
            worker_urn=command.worker_urn,
            strategy_urn=command.strategy_urn,
            capability_urn=command.capability_urn,
            previous_journal_urn=previous_urn,
            journal_hash=jhash,
            confidence=confidence,
            rationale=command.rationale,
            evidence_references=command.evidence_references,
            risk_assumptions=command.risk_assumptions,
            invalidation_criteria=invalidation,
            expected_outcome=outcome,
            expected_horizon=horizon,
            created_at=datetime.utcnow()
        )
        
        self.repository.append(entry)
        
        event = DecisionJournalAppended(
            journal_urn=entry.journal_urn,
            thesis_urn=entry.thesis_urn,
            worker_urn=entry.worker_urn,
            strategy_urn=entry.strategy_urn,
            capability_urn=entry.capability_urn,
            previous_journal_urn=entry.previous_journal_urn,
            journal_hash=entry.journal_hash.hash_value,
            created_at=entry.created_at
        )
        self.event_bus.publish(event)
        
        return entry
