from dataclasses import dataclass
from typing import Dict, Optional, List

@dataclass(frozen=True)
class OutcomeSequenceIdentity:
    outcome_id: str
    sequence_id: int

@dataclass(frozen=True)
class AttributionIdentity:
    attribution_id: str
    outcome_id: str
    source_context_id: str
    attribution_generation: int
    outcome_sequence: int
    parent_attribution_id: Optional[str] = None

@dataclass(frozen=True)
class ContributionWeight:
    role_identifier: str
    target_identity: str
    weight_fraction: float

@dataclass(frozen=True)
class PolicyInputSnapshot:
    policy_version: str
    weight_model: str
    normalization_strategy: str
    rounding_strategy: str
    allocation_ordering: str
    role_weights: Dict[str, float]
    currency_precision: int

@dataclass(frozen=True)
class GovernanceAuditContext:
    approval_reference: str
    approval_timestamp: str
    approved_by: str
    approval_reason: str

@dataclass(frozen=True)
class AttributedValue:
    target_identity: str
    gross_pnl: float
    attributed_pnl: float
    attribution_percentage: float
    currency: str
