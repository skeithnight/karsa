from decimal import Decimal
from karsa.governance_engine.domain.models import TrustScoreLedgerEntry
from karsa.governance_engine.domain.events import GovernanceActionExecuted

class ApplyGovernanceService:
    def __init__(self, repo, event_bus):
        self.repo = repo
        self.event_bus = event_bus

    def execute(self, ledger_urn, subject_urn, prev_urn, new_score, action_type):
        entry = TrustScoreLedgerEntry(ledger_urn, subject_urn, prev_urn or "ROOT", Decimal(new_score))
        self.repo.save(entry)
        self.event_bus.publish(GovernanceActionExecuted(subject_urn, action_type))
        return entry
