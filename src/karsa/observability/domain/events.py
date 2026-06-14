from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from karsa.domain.events import DomainEvent

@dataclass
class SpanStartedEvent(DomainEvent):
    trace_id: str = ""
    span_id: str = ""
    name: str = ""
    start_time: datetime = field(default_factory=lambda: datetime.utcnow())
    parent_span_id: Optional[str] = None
    span_kind: str = "INTERNAL"
    correlation_context: Dict[str, str] = field(default_factory=dict)

@dataclass
class SpanClosedEvent(DomainEvent):
    trace_id: str = ""
    span_id: str = ""
    end_time: datetime = field(default_factory=lambda: datetime.utcnow())
    status: str = "OK"
    correlation_context: Dict[str, str] = field(default_factory=dict)

@dataclass
class SpanEventLoggedEvent(DomainEvent):
    trace_id: str = ""
    span_id: str = ""
    event_id: str = ""
    name: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.utcnow())
    payload: Dict[str, Any] = field(default_factory=dict)
