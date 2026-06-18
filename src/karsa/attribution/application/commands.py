from dataclasses import dataclass
from typing import Optional
from karsa.attribution.domain.model.value_objects import GovernanceAuditContext

@dataclass
class ProcessRealizedOutcomeCommand:
    outcome_id: str
    sequence_id: int
    source_context_id: str
    gross_pnl: float
    currency: str

@dataclass
class ApplyAttributionRestatementCommand:
    outcome_id: str
    sequence_id: int
    gross_pnl: float
    currency: str
    source_context_id: str
    governance_audit_context: GovernanceAuditContext
