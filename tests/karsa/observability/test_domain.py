from karsa.observability.domain.models import TraceContext, MetricSnapshot
from decimal import Decimal

def test_trace_context():
    ctx = TraceContext("t1", "c1", "ca1", "sig")
    assert ctx.trace_id == "t1"
    
def test_metric_snapshot():
    m = MetricSnapshot("cpu", Decimal("45.5"), {})
    assert m.value == Decimal("45.5")
