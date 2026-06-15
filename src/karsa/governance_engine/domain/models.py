from dataclasses import dataclass
from enum import Enum
from decimal import Decimal

class GovernanceTarget(Enum):
    WORKER = "WORKER"
    STRATEGY = "STRATEGY"
    THESIS = "THESIS"
    CAPABILITY = "CAPABILITY"
    PORTFOLIO = "PORTFOLIO"

@dataclass(frozen=True)
class GovernanceSubject:
    subject_urn: str
    target_type: GovernanceTarget

@dataclass(frozen=True)
class TrustScoreLedgerEntry:
    ledger_urn: str
    subject_urn: str
    previous_ledger_urn: str
    trust_score: Decimal
