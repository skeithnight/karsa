
from karsa.observability.infrastructure.repositories import PostgresTraceRepository, PostgresSnapshotRepository, MinIOArchivalRepository
from karsa.observability.infrastructure.workers import ProjectionDebouncer, RehydrationWorker
from karsa.observability.domain.models import TraceContext, TraceSpan, WorkerState, QueueState, MetricSnapshot
from datetime import datetime
from decimal import Decimal
import pytest

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

def test_archival_fail_open():
    repo = MinIOArchivalRepository()
    with pytest.raises(RuntimeError, match="Archival failed"):
        repo.export_to_cold_storage("FAIL_DATE")

def test_rehydration_worker():
    cursor = MockCursor()
    repo = MinIOArchivalRepository(cursor)
    worker = RehydrationWorker(repo)
    
    worker.rehydrate("s3://test.parquet", "123hash")
    assert "INSERT INTO postgres_archive_sandbox.traces" in cursor.queries[0][0]
    
    with pytest.raises(ValueError, match="Checksum mismatch"):
        worker.rehydrate("s3://CORRUPTED.parquet", "badhash")
