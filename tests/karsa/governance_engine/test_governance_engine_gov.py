from karsa.governance_engine.application.services import ApplyGovernanceService
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
