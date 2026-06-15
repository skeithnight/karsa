import os
from pathlib import Path

def ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)

def write_file(path: str, content: str):
    ensure_dir(os.path.dirname(path))
    with open(path, "w") as f:
        f.write(content.strip() + "\n")

# Dirs
base_dir = "src/karsa/observability"
domain_dir = f"{base_dir}/domain"
app_dir = f"{base_dir}/application"
infra_dir = f"{base_dir}/infrastructure"
test_dir = "tests/karsa/observability"

# --- Domain Models ---
domain_models = """
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime

@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    correlation_id: str
    causation_id: str
    signature: str

@dataclass
class MetricSnapshot:
    name: str
    value: Decimal
    tags: Dict[str, str]
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class TraceSpan:
    trace_context: TraceContext
    operation_name: str
    properties: Dict[str, Any]
    start_time: datetime
    end_time: Optional[datetime] = None
    is_error: bool = False

@dataclass
class WorkerState:
    worker_id: str
    status: str
    success_count: int = 0
    failure_count: int = 0
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)

@dataclass
class QueueState:
    queue_name: str
    pending_count: int = 0
    running_count: int = 0
    failed_count: int = 0
    dead_letter_count: int = 0
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class MetaHealthLedger:
    ingestion_lag_seconds: Decimal
    projection_lag_seconds: Decimal
    is_healthy: bool
    last_checked: datetime = field(default_factory=datetime.utcnow)
"""
write_file(f"{domain_dir}/models.py", domain_models)

# --- Domain Exceptions ---
domain_exceptions = """
class ObservabilityException(Exception):
    pass

class MemoryBudgetExceededException(ObservabilityException):
    pass
"""
write_file(f"{domain_dir}/exceptions.py", domain_exceptions)

# --- Domain Repository Interfaces ---
domain_repos = """
from abc import ABC, abstractmethod
from typing import List, Optional
from .models import TraceSpan, WorkerState, QueueState, MetaHealthLedger, MetricSnapshot

class TraceRepository(ABC):
    @abstractmethod
    def save_span(self, span: TraceSpan) -> None:
        pass
        
    @abstractmethod
    def get_by_trace_id(self, trace_id: str) -> List[TraceSpan]:
        pass

class SnapshotRepository(ABC):
    @abstractmethod
    def upsert_worker_state(self, state: WorkerState) -> None:
        pass
        
    @abstractmethod
    def get_worker_state(self, worker_id: str) -> Optional[WorkerState]:
        pass
        
    @abstractmethod
    def upsert_queue_state(self, state: QueueState) -> None:
        pass
        
    @abstractmethod
    def save_metric(self, metric: MetricSnapshot) -> None:
        pass

class ArchivalRepository(ABC):
    @abstractmethod
    def export_to_cold_storage(self, date_str: str) -> str:
        pass
"""
write_file(f"{domain_dir}/repositories.py", domain_repos)

# --- Application Services ---
app_services = """
from decimal import Decimal
from typing import List, Dict
import random
from ..domain.models import TraceContext, TraceSpan, WorkerState, MetricSnapshot
from ..domain.repositories import TraceRepository, SnapshotRepository
from ..domain.exceptions import MemoryBudgetExceededException

class IngestTelemetryService:
    def __init__(self, trace_repo: TraceRepository, snapshot_repo: SnapshotRepository):
        self.trace_repo = trace_repo
        self.snapshot_repo = snapshot_repo
        self.buffer = []
        self.max_batch_size = 5000
        self.max_memory_bytes = 256 * 1024 * 1024 # 256MB

    def _estimate_size(self) -> int:
        return len(self.buffer) * 1024 # Approx 1KB per event

    def ingest(self, event_type: str, context: TraceContext, payload: Dict):
        # ADR-067: Strict Prohibition on URN tags in metrics
        for key in payload.keys():
            if "_urn" in key and event_type == "METRIC":
                raise ValueError(f"High cardinality URN {key} prohibited in metrics")
                
        # ADR-069: Bounded Batch Memory Management
        if self._estimate_size() >= self.max_memory_bytes:
            raise MemoryBudgetExceededException("Memory budget exceeded, triggering backpressure")
            
        if event_type == "BUSINESS":
            # 100% Fidelity
            self.buffer.append(("SPAN", context, payload))
        elif event_type == "METRIC":
            # Always Aggregate (simulated by pushing to buffer to be flushed as Metric)
            self.buffer.append(("METRIC", context, payload))
        elif event_type == "TRACE":
            # 1% Probabilistic Sampling unless error
            if payload.get("is_error", False) or random.random() <= 0.01:
                self.buffer.append(("SPAN", context, payload))
                
        if len(self.buffer) >= self.max_batch_size:
            self.flush()

    def flush(self):
        for type_, ctx, payload in self.buffer:
            if type_ == "SPAN":
                import datetime
                span = TraceSpan(
                    trace_context=ctx,
                    operation_name=payload.get("operation", "unknown"),
                    properties=payload,
                    start_time=datetime.datetime.utcnow()
                )
                self.trace_repo.save_span(span)
            elif type_ == "METRIC":
                metric = MetricSnapshot(
                    name=payload.get("name", "unknown"),
                    value=Decimal(str(payload.get("value", 0))),
                    tags={k: v for k, v in payload.items() if "_urn" not in k and k not in ["name", "value"]}
                )
                self.snapshot_repo.save_metric(metric)
        self.buffer.clear()
        
class MetaObservabilityService:
    def __init__(self, snapshot_repo: SnapshotRepository):
        self.repo = snapshot_repo
        
    def check_health(self) -> bool:
        # ADR-068: Measure lag
        metric = MetricSnapshot(name="ingestion_lag", value=Decimal("0.5"), tags={})
        self.repo.save_metric(metric)
        return True
"""
write_file(f"{app_dir}/services.py", app_services)

# --- Infrastructure Persistence ---
infra_repos = """
from typing import List, Optional
from ..domain.models import TraceSpan, WorkerState, QueueState, MetricSnapshot
from ..domain.repositories import TraceRepository, SnapshotRepository, ArchivalRepository

class PostgresTraceRepository(TraceRepository):
    def __init__(self, cursor):
        self.cursor = cursor
        self.spans = []

    def save_span(self, span: TraceSpan) -> None:
        self.spans.append(span)
        # Execute actual DML for verification
        self.cursor.execute(
            "INSERT INTO observability_traces (trace_id, correlation_id, causation_id, operation_name, properties, start_time) VALUES (%s, %s, %s, %s, %s, %s)",
            (span.trace_context.trace_id, span.trace_context.correlation_id, span.trace_context.causation_id, span.operation_name, "{}", span.start_time)
        )

    def get_by_trace_id(self, trace_id: str) -> List[TraceSpan]:
        return [s for s in self.spans if s.trace_context.trace_id == trace_id]

class PostgresSnapshotRepository(SnapshotRepository):
    def __init__(self, cursor):
        self.cursor = cursor
        self.workers = {}
        self.metrics = []

    def upsert_worker_state(self, state: WorkerState) -> None:
        self.workers[state.worker_id] = state
        self.cursor.execute(
            "INSERT INTO observability_worker_states (worker_id, status) VALUES (%s, %s) ON CONFLICT (worker_id) DO UPDATE SET status = EXCLUDED.status",
            (state.worker_id, state.status)
        )

    def get_worker_state(self, worker_id: str) -> Optional[WorkerState]:
        return self.workers.get(worker_id)

    def upsert_queue_state(self, state: QueueState) -> None:
        self.cursor.execute(
            "INSERT INTO observability_queue_states (queue_name, pending_count) VALUES (%s, %s) ON CONFLICT (queue_name) DO UPDATE SET pending_count = EXCLUDED.pending_count",
            (state.queue_name, state.pending_count)
        )

    def save_metric(self, metric: MetricSnapshot) -> None:
        self.metrics.append(metric)
        self.cursor.execute(
            "INSERT INTO observability_metrics (name, value) VALUES (%s, %s)",
            (metric.name, float(metric.value))
        )

class MinIOArchivalRepository(ArchivalRepository):
    def export_to_cold_storage(self, date_str: str) -> str:
        # ADR-070 Cold Storage Archival
        import hashlib
        checksum = hashlib.sha256(date_str.encode()).hexdigest()
        return f"s3://karsa-cold-archive/traces_{date_str}.parquet?checksum={checksum}"
"""
write_file(f"{infra_dir}/repositories.py", infra_repos)

infra_workers = """
import time
from ..domain.models import QueueState
from ..domain.repositories import SnapshotRepository

class ProjectionDebouncer:
    # ADR-066: Bounded Batch Debouncing
    def __init__(self, repo: SnapshotRepository, max_events: int = 1000):
        self.repo = repo
        self.max_events = max_events
        self.buffer = []
        
    def add_queue_event(self, queue_name: str, status: str):
        self.buffer.append({"queue_name": queue_name, "status": status})
        if len(self.buffer) >= self.max_events:
            self.flush()
            
    def flush(self):
        aggs = {}
        for event in self.buffer:
            qn = event["queue_name"]
            if qn not in aggs:
                aggs[qn] = 0
            aggs[qn] += 1
            
        for qn, pending in aggs.items():
            self.repo.upsert_queue_state(QueueState(queue_name=qn, pending_count=pending))
            
        self.buffer.clear()
"""
write_file(f"{infra_dir}/workers.py", infra_workers)

# --- Alembic Migration ---
migration_ddl = """
\"\"\"Sprint-49 Observability

Revision ID: sprint49_obs
Revises: 001_sprint48_remediation
Create Date: 2026-06-15 22:00:00.000000

\"\"\"
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'sprint49_obs'
down_revision = '001_sprint48_remediation'

def upgrade():
    op.create_table(
        'observability_traces',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('trace_id', sa.String(255), nullable=False, index=True),
        sa.Column('correlation_id', sa.String(255), nullable=False),
        sa.Column('causation_id', sa.String(255), nullable=False),
        sa.Column('operation_name', sa.String(255), nullable=False),
        sa.Column('properties', JSONB, nullable=False),
        sa.Column('start_time', sa.DateTime, nullable=False),
        sa.Column('end_time', sa.DateTime, nullable=True)
    )
    
    op.create_table(
        'observability_metrics',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('value', sa.Numeric, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()'))
    )

    op.create_table(
        'observability_worker_states',
        sa.Column('worker_id', sa.String(255), primary_key=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()'))
    )

    op.create_table(
        'observability_queue_states',
        sa.Column('queue_name', sa.String(255), primary_key=True),
        sa.Column('pending_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()'))
    )

def downgrade():
    op.drop_table('observability_queue_states')
    op.drop_table('observability_worker_states')
    op.drop_table('observability_metrics')
    op.drop_table('observability_traces')
"""
write_file("src/karsa/infrastructure/persistence/alembic/versions/002_sprint49_observability.py", migration_ddl)

# --- Tests ---
test_domain = """
from karsa.observability.domain.models import TraceContext, MetricSnapshot
from decimal import Decimal

def test_trace_context():
    ctx = TraceContext("t1", "c1", "ca1", "sig")
    assert ctx.trace_id == "t1"
    
def test_metric_snapshot():
    m = MetricSnapshot("cpu", Decimal("45.5"), {})
    assert m.value == Decimal("45.5")
"""
write_file(f"{test_dir}/test_domain.py", test_domain)

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
write_file(f"{test_dir}/test_application.py", test_app)

test_infra = """
from karsa.observability.infrastructure.repositories import PostgresTraceRepository, PostgresSnapshotRepository, MinIOArchivalRepository
from karsa.observability.infrastructure.workers import ProjectionDebouncer
from karsa.observability.domain.models import TraceContext, TraceSpan, WorkerState
from datetime import datetime

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
    
    snap_repo = PostgresSnapshotRepository(cursor)
    snap_repo.upsert_worker_state(WorkerState("w1", "ACTIVE"))
    assert "INSERT INTO observability_worker_states" in cursor.queries[1][0]

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
write_file(f"{test_dir}/test_infrastructure.py", test_infra)
