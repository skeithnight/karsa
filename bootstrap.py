import os
import pathlib

files = {
    "src/karsa/performance_engine/domain/models.py": """from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass(frozen=True)
class PerformanceEvaluation:
    eval_urn: str
    outcome_urn: str
    journal_urn: str
    forecast_error: Decimal
    created_at: datetime
""",
    "src/karsa/performance_engine/domain/events.py": """from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class PerformanceEvaluated:
    eval_urn: str
    outcome_urn: str
    created_at: datetime
""",
    "src/karsa/performance_engine/application/services.py": """from karsa.performance_engine.domain.models import PerformanceEvaluation
from karsa.performance_engine.domain.events import PerformanceEvaluated
from datetime import datetime
from decimal import Decimal

class EvaluatePerformanceService:
    def __init__(self, repo, event_bus):
        self.repo = repo
        self.event_bus = event_bus
        
    def execute(self, eval_urn: str, outcome_urn: str, journal_urn: str, expected: Decimal, actual: Decimal):
        error = abs(expected - actual)
        eval = PerformanceEvaluation(eval_urn, outcome_urn, journal_urn, error, datetime.utcnow())
        self.repo.save(eval)
        self.event_bus.publish(PerformanceEvaluated(eval_urn, outcome_urn, eval.created_at))
        return eval
""",
    "tests/karsa/performance_engine/test_perf.py": """from decimal import Decimal
from karsa.performance_engine.application.services import EvaluatePerformanceService

class DummyRepo:
    def save(self, e): pass

class DummyBus:
    def publish(self, e): pass

def test_perf_service():
    svc = EvaluatePerformanceService(DummyRepo(), DummyBus())
    eval = svc.execute("e1", "o1", "j1", Decimal("100"), Decimal("90"))
    assert eval.forecast_error == Decimal("10")
""",
    "src/karsa/attribution_engine/domain/models.py": """from dataclasses import dataclass
from typing import Dict
from decimal import Decimal

@dataclass(frozen=True)
class FactorModelVersion:
    version_urn: str
    model_hash: str

@dataclass(frozen=True)
class AttributionDecomposition:
    attrib_urn: str
    eval_urn: str
    factor_model_version_urn: str
    causal_fractions: Dict[str, Decimal]
""",
    "src/karsa/attribution_engine/domain/events.py": """from dataclasses import dataclass

@dataclass(frozen=True)
class AttributionResolved:
    attrib_urn: str
    factor_model_hash: str

@dataclass(frozen=True)
class ResearchFeedbackCandidateCreated:
    attrib_urn: str
    thesis_urn: str

@dataclass(frozen=True)
class CapabilityFeedbackCandidateCreated:
    attrib_urn: str
    capability_urn: str
""",
    "src/karsa/attribution_engine/application/services.py": """from decimal import Decimal
from karsa.attribution_engine.domain.models import AttributionDecomposition
from karsa.attribution_engine.domain.events import AttributionResolved, ResearchFeedbackCandidateCreated, CapabilityFeedbackCandidateCreated

class DecomposeAttributionService:
    def __init__(self, repo, event_bus):
        self.repo = repo
        self.event_bus = event_bus

    def execute(self, attrib_urn, eval_urn, fm_urn, fm_hash, thesis_urn, capability_urn):
        decomp = AttributionDecomposition(attrib_urn, eval_urn, fm_urn, {"thesis": Decimal("0.5"), "luck": Decimal("0.5")})
        self.repo.save(decomp)
        self.event_bus.publish(AttributionResolved(attrib_urn, fm_hash))
        if thesis_urn:
            self.event_bus.publish(ResearchFeedbackCandidateCreated(attrib_urn, thesis_urn))
        if capability_urn:
            self.event_bus.publish(CapabilityFeedbackCandidateCreated(attrib_urn, capability_urn))
        return decomp
""",
    "tests/karsa/attribution_engine/test_attrib.py": """from karsa.attribution_engine.application.services import DecomposeAttributionService

class DummyRepo:
    def save(self, e): pass

class DummyBus:
    def publish(self, e): pass

def test_attrib_service():
    svc = DecomposeAttributionService(DummyRepo(), DummyBus())
    d = svc.execute("a1", "e1", "fm1", "hash1", "t1", "c1")
    assert d.attrib_urn == "a1"
""",
    "src/karsa/governance_engine/domain/models.py": """from dataclasses import dataclass
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
""",
    "src/karsa/governance_engine/domain/events.py": """from dataclasses import dataclass

@dataclass(frozen=True)
class GovernanceActionExecuted:
    subject_urn: str
    action_type: str
""",
    "src/karsa/governance_engine/application/services.py": """from decimal import Decimal
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
""",
    "tests/karsa/governance_engine/test_gov.py": """from karsa.governance_engine.application.services import ApplyGovernanceService
from karsa.governance_engine.domain.models import GovernanceTarget, GovernanceSubject

class DummyRepo:
    def save(self, e): pass

class DummyBus:
    def publish(self, e): pass

def test_gov_service():
    subj = GovernanceSubject("w1", GovernanceTarget.WORKER)
    svc = ApplyGovernanceService(DummyRepo(), DummyBus())
    e = svc.execute("l1", subj.subject_urn, None, "0.95", "PROMOTION")
    assert e.trust_score > 0
"""
}

for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

print("Generated full Sprint-48 scope files.")
