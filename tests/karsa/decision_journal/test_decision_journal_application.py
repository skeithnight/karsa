import pytest
from datetime import datetime
from typing import Optional, List
from karsa.decision_journal.application.services import AppendDecisionJournalCommand, AppendDecisionJournalService
from karsa.decision_journal.domain.repository.repositories import DecisionJournalRepository
from karsa.decision_journal.domain.models import DecisionJournalEntry

class DummyRepo(DecisionJournalRepository):
    def __init__(self):
        self.entries = []
    def append(self, entry: DecisionJournalEntry) -> None:
        self.entries.append(entry)
    def get_by_urn(self, urn: str) -> Optional[DecisionJournalEntry]:
        pass  # pragma: no cover
    def fetch_latest_by_thesis(self, thesis_urn: str):
        thesis_entries = [e for e in self.entries if e.thesis_urn == thesis_urn]
        if thesis_entries:
            return thesis_entries[-1]
        return None
    def fetch_latest_by_worker(self, worker_urn: str):
        pass  # pragma: no cover
    def fetch_lineage(self, journal_urn: str):
        pass  # pragma: no cover
    def fetch_by_time_range(self, start: datetime, end: datetime):
        pass  # pragma: no cover

class DummyEventBus:
    def __init__(self):
        self.events = []
    def publish(self, event):
        self.events.append(event)

def test_append_service():
    repo = DummyRepo()
    bus = DummyEventBus()
    svc = AppendDecisionJournalService(repo, bus)
    
    cmd = AppendDecisionJournalCommand(
        journal_urn="j1", thesis_urn="t1", worker_urn="w1", strategy_urn="s1", capability_urn="c1",
        confidence_value="0.9", rationale="Because.", evidence_references=[],
        risk_assumptions=[], invalidation_criteria_text="Invalid if...",
        expected_outcome_value="100.0", expected_outcome_metric="price", expected_horizon_days=30
    )
    
    entry = svc.execute(cmd)
    assert entry.previous_journal_urn is None
    assert entry.expected_outcome.target_value == 100.0
    assert len(repo.entries) == 1
    assert len(bus.events) == 1
    
    cmd2 = AppendDecisionJournalCommand(
        journal_urn="j2", thesis_urn="t1", worker_urn="w1", strategy_urn="s1", capability_urn="c1",
        confidence_value="0.8", rationale="Updated.", evidence_references=[],
        risk_assumptions=[], invalidation_criteria_text="Invalid if...",
        expected_outcome_value="110.0", expected_outcome_metric="price", expected_horizon_days=30
    )
    entry2 = svc.execute(cmd2)
    assert entry2.previous_journal_urn == "j1"
    assert entry2.journal_hash.hash_value != entry.journal_hash.hash_value
    assert len(repo.entries) == 2
    assert len(bus.events) == 2
