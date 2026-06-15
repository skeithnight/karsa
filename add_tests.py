import os

test_infra = """
from karsa.observability.infrastructure.repositories import PostgresTraceRepository, PostgresSnapshotRepository, MinIOArchivalRepository
from karsa.observability.infrastructure.workers import ProjectionDebouncer
from karsa.observability.domain.models import TraceContext, TraceSpan, WorkerState, QueueState, MetricSnapshot
from datetime import datetime
from decimal import Decimal

class MockCursor:
    def __init__(self):
        self.queries = []
    def execute(self, query, params=None):
        self.queries.append((query, params))

def test_postgres_repos():
    cursor = MockCursor()
    trace_repo = PostgresTraceRepository(cursor)
    ctx = TraceContext("t1", "c1", "ca1", "sig")
    span = TraceSpan(ctx, "op", {}, datetime.utcnow())
    trace_repo.save_span(span)
    assert "INSERT INTO observability_traces" in cursor.queries[0][0]
    fetched = trace_repo.get_by_trace_id("t1")
    assert len(fetched) == 1
    
    snap_repo = PostgresSnapshotRepository(cursor)
    snap_repo.upsert_worker_state(WorkerState("w1", "ACTIVE"))
    assert "INSERT INTO observability_worker_states" in cursor.queries[1][0]
    fetched_ws = snap_repo.get_worker_state("w1")
    assert fetched_ws.status == "ACTIVE"

    snap_repo.upsert_queue_state(QueueState("q1", 10))
    assert "INSERT INTO observability_queue_states" in cursor.queries[2][0]

    snap_repo.save_metric(MetricSnapshot("cpu", Decimal("10"), {}))
    assert "INSERT INTO observability_metrics" in cursor.queries[3][0]

def test_debouncer():
    cursor = MockCursor()
    repo = PostgresSnapshotRepository(cursor)
    debouncer = ProjectionDebouncer(repo, max_events=3)
    
    debouncer.add_queue_event("q1", "PENDING")
    debouncer.add_queue_event("q1", "PENDING")
    assert len(cursor.queries) == 0
    
    debouncer.add_queue_event("q1", "PENDING") # Flushes
    assert len(cursor.queries) == 1
    assert cursor.queries[0][1] == ("q1", 3)

def test_archival():
    repo = MinIOArchivalRepository()
    path = repo.export_to_cold_storage("2026-06-15")
    assert "s3://karsa-cold-archive" in path
    assert "checksum=" in path
"""
with open("tests/karsa/observability/test_infrastructure.py", "w") as f:
    f.write(test_infra)

test_app = """
import pytest
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
    assert svc.check_health() is True
"""
with open("tests/karsa/observability/test_application.py", "w") as f:
    f.write(test_app)
