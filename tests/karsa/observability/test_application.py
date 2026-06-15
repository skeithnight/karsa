
import pytest
import datetime
from karsa.observability.application.services import IngestTelemetryService, MetaObservabilityService
from karsa.observability.domain.models import TraceContext
from karsa.observability.domain.exceptions import MemoryBudgetExceededException

class MockTraceRepo:
    def save_span(self, span): pass
class MockSnapshotRepo:
    def save_metric(self, metric): pass

def test_ingest_telemetry_sampling():
    svc = IngestTelemetryService(MockTraceRepo(), MockSnapshotRepo())
    ctx = TraceContext("t1", "c1", "ca1", "sig")
    
    # 100% fidelity business event
    svc.ingest("BUSINESS", ctx, {"operation": "DecisionCaptured"})
    assert len(svc.buffer) == 1
    
    # Trace sampled out (probabilistic)
    import random
    random.seed(42) # Ensure random > 0.01
    svc.ingest("TRACE", ctx, {"operation": "DebugLog"})
    assert len(svc.buffer) == 1 # unchanged
    
    # Trace error forced capture
    svc.ingest("TRACE", ctx, {"operation": "ErrorLog", "is_error": True})
    assert len(svc.buffer) == 2

    svc.flush()
    assert len(svc.buffer) == 0

def test_ingest_metric_flush():
    svc = IngestTelemetryService(MockTraceRepo(), MockSnapshotRepo())
    ctx = TraceContext("t1", "c1", "ca1", "sig")
    svc.ingest("METRIC", ctx, {"name": "cpu", "value": 50, "host": "localhost"})
    svc.flush()
    assert len(svc.buffer) == 0

def test_cardinality_governance():
    svc = IngestTelemetryService(MockTraceRepo(), MockSnapshotRepo())
    ctx = TraceContext("t1", "c1", "ca1", "sig")
    with pytest.raises(ValueError, match="High cardinality URN"):
        svc.ingest("METRIC", ctx, {"thesis_urn": "th_123", "value": 1})

def test_memory_budget_exceeded():
    svc = IngestTelemetryService(MockTraceRepo(), MockSnapshotRepo())
    svc.max_memory_bytes = 100 # Low limit
    ctx = TraceContext("t1", "c1", "ca1", "sig")
    with pytest.raises(MemoryBudgetExceededException):
        for _ in range(100):
            svc.ingest("BUSINESS", ctx, {"operation": "op"})
            
def test_meta_observability():
    repo = MockSnapshotRepo()
    svc = MetaObservabilityService(repo)
    # No lag
    now = datetime.datetime.utcnow()
    assert svc.check_health(now) is True
    # Major lag
    old = now - datetime.timedelta(seconds=600)
    assert svc.check_health(old) is False
