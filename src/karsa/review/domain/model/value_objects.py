from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal

class ReviewTargetType(Enum):
    WORKER = "WORKER"
    THESIS_VERSION = "THESIS_VERSION"
    STRATEGY = "STRATEGY"
    PORTFOLIO = "PORTFOLIO"
    BINDING = "BINDING"

class ReviewSessionType(Enum):
    AUTOMATED_ANOMALY = "AUTOMATED_ANOMALY"
    CANARY_AUDIT = "CANARY_AUDIT"
    MANUAL_POST_MORTEM = "MANUAL_POST_MORTEM"

class ReviewVerdictOutcome(Enum):
    PASS = "PASS"
    WARNING_RETRY = "WARNING_RETRY"
    CRITICAL_DEPRECATE = "CRITICAL_DEPRECATE"
    SUSPEND_RECALIBRATE = "SUSPEND_RECALIBRATE"

class LearningFeedbackCategory(Enum):
    THESIS = "THESIS"
    RESEARCH = "RESEARCH"
    CAPITAL = "CAPITAL"
    GOVERNANCE = "GOVERNANCE"
    WORKER = "WORKER"

class EvidenceRetentionClass(Enum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"
    PERMANENT = "PERMANENT"


@dataclass(frozen=True)
class ReviewTarget:
    target_type: ReviewTargetType
    target_id: str
    target_version: Optional[str] = None


@dataclass(frozen=True)
class LLMConfigSnapshot:
    model_name: str
    temperature: Decimal
    seed: int


@dataclass(frozen=True)
class ReviewFinding:
    finding_id: str
    finding_type: str
    severity: str
    description: str
    created_at: datetime


@dataclass(frozen=True)
class ReviewEvidence:
    evidence_id: str
    source_type: str
    source_reference_id: str
    evidence_hash: str
    evidence_summary: str
    retention_class: EvidenceRetentionClass
    created_at: datetime
    llm_config: Optional[LLMConfigSnapshot] = None


@dataclass(frozen=True)
class ReviewVerdict:
    verdict_id: str
    outcome_rating: ReviewVerdictOutcome
    justification: str
    created_at: datetime
