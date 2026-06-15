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
