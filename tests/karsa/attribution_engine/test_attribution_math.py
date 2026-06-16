from decimal import Decimal
from karsa.attribution_engine.application.services import DecomposeAttributionService

class MockJournalRepo:
    def get_by_urn(self, urn):
        class J: expected_outcome = Decimal("100")
        return J()

class MockUoW:
    def __init__(self): self.outbox = self
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def add(self, e): pass
    def commit(self): pass

class MockRepo:
    def save(self, e): pass

def test_dynamic_decomposition():
    svc = DecomposeAttributionService(MockRepo(), MockUoW(), MockJournalRepo())
    # Forecast error = 20, Expected = 100 -> thesis fraction = 80/100 = 0.8
    decomp = svc.execute("a1", "e1", "fm1", "hash", "t1", "j1", Decimal("20"))
    assert decomp.causal_fractions["thesis"] == Decimal("0.8")
    assert decomp.causal_fractions["luck"] == Decimal("0.2")

    # Forecast error = 90, Expected = 100 -> thesis fraction = 10/100 = 0.1
    decomp2 = svc.execute("a2", "e2", "fm1", "hash", "t1", "j1", Decimal("90"))
    assert decomp2.causal_fractions["thesis"] == Decimal("0.1")
    assert decomp2.causal_fractions["luck"] == Decimal("0.9")
