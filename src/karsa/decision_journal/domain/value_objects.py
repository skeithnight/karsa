from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from karsa.decision_journal.domain.exceptions import InvalidConfidenceError
import hashlib

@dataclass(frozen=True)
class ConfidenceLevel:
    value: Decimal

    def __post_init__(self):
        if not (Decimal("0.0") <= self.value <= Decimal("1.0")):
            raise InvalidConfidenceError("Confidence must be between 0.0 and 1.0")

@dataclass(frozen=True)
class InvalidationCriteria:
    criteria: str

    def __post_init__(self):
        if not self.criteria.strip():
            raise ValueError("Criteria cannot be empty")

@dataclass(frozen=True)
class ExpectedOutcome:
    target_value: Decimal
    metric_type: str

@dataclass(frozen=True)
class ExpectedHorizon:
    days: int
    
    def __post_init__(self):
        if self.days <= 0:
            raise ValueError("Expected horizon must be strictly positive")

@dataclass(frozen=True)
class JournalHash:
    hash_value: str
    
    @staticmethod
    def generate(urn: str, thesis_urn: str, previous_hash: Optional[str]) -> 'JournalHash':
        base = f"{urn}|{thesis_urn}|{previous_hash or 'ROOT'}"
        return JournalHash(hashlib.sha256(base.encode('utf-8')).hexdigest())
