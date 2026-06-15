
from decimal import Decimal
from typing import List, Dict, Optional
import random
import datetime
from ..domain.models import TraceContext, TraceSpan, WorkerState, MetricSnapshot
from ..domain.repositories import TraceRepository, SnapshotRepository, ArchivalRepository
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
            self.buffer.append(("SPAN", context, payload, datetime.datetime.utcnow()))
        elif event_type == "METRIC":
            # Always Aggregate (simulated by pushing to buffer to be flushed as Metric)
            self.buffer.append(("METRIC", context, payload, datetime.datetime.utcnow()))
        elif event_type == "TRACE":
            # 1% Probabilistic Sampling unless error
            if payload.get("is_error", False) or random.random() <= 0.01:
                self.buffer.append(("SPAN", context, payload, datetime.datetime.utcnow()))
                
        if len(self.buffer) >= self.max_batch_size:
            self.flush()

    def flush(self):
        for type_, ctx, payload, ingested_at in self.buffer:
            if type_ == "SPAN":
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
        
    def check_health(self, last_ingested_event_timestamp: Optional[datetime.datetime]) -> bool:
        # F-01: Calculate real lag evidence
        now = datetime.datetime.utcnow()
        if last_ingested_event_timestamp:
            lag = (now - last_ingested_event_timestamp).total_seconds()
        else:
            lag = 0.0
            
        metric = MetricSnapshot(name="ingestion_lag", value=Decimal(str(lag)), tags={})
        self.repo.save_metric(metric)
        return lag < 300.0 # Healthy if lag < 5 minutes
