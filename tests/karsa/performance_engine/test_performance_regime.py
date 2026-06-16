from decimal import Decimal
from karsa.performance_engine.application.services import EvaluatePerformanceService

class MockUoW:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def commit(self): pass

class MockRepo:
    def save(self, e): pass

def test_performance_regime():
    svc = EvaluatePerformanceService(MockRepo(), MockUoW())
    eval_obj = svc.execute("e1", "o1", "j1", "100", "90", {"bull": 0.8, "bear": 0.1, "sideways": 0.1})
    assert eval_obj.forecast_error == Decimal("10")
    assert eval_obj.regime.bull == Decimal("0.8")
