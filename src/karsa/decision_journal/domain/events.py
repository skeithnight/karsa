from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass(frozen=True)
class DecisionJournalAppended:
    journal_urn: str
    thesis_urn: str
    worker_urn: str
    strategy_urn: Optional[str]
    capability_urn: Optional[str]
    previous_journal_urn: Optional[str]
    journal_hash: str
    created_at: datetime
