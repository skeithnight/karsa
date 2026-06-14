from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Any
from karsa.shared.domain.aggregate import VersionedAggregate

class SpanStatus(Enum):
    OK = auto()
    ERROR = auto()

class SpanKind(Enum):
    INTERNAL = auto()
    CLIENT = auto()
    SERVER = auto()
    PRODUCER = auto()
    CONSUMER = auto()

class TraceRetentionTier(Enum):
    HOT = auto()
    WARM = auto()
    COLD = auto()

@dataclass(frozen=True)
class AttributionReference:
    attribution_id: str

@dataclass(frozen=True)
class DecisionJournalReference:
    decision_journal_id: str

@dataclass(frozen=True)
class CorrelationContext:
    trace_id: str
    workflow_id: Optional[str] = None
    research_run_id: Optional[str] = None
    thesis_id: Optional[str] = None
    worker_id: Optional[str] = None
    capability_execution_id: Optional[str] = None
    provider_execution_id: Optional[str] = None
    governance_decision_id: Optional[str] = None
    decision_journal_id: Optional[str] = None
    review_session_id: Optional[str] = None
    attribution_id: Optional[str] = None
    portfolio_id: Optional[str] = None

@dataclass
class SpanEvent:
    event_id: str
    name: str
    timestamp: datetime
    payload: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Span(VersionedAggregate):
    span_id: str = ""
    trace_id: str = ""
    name: str = ""
    start_time: datetime = field(default_factory=lambda: datetime.utcnow())
    parent_span_id: Optional[str] = None
    span_kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.OK
    end_time: Optional[datetime] = None
    events: List[SpanEvent] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    attribution_ref: Optional[AttributionReference] = None
    journal_ref: Optional[DecisionJournalReference] = None
    review_session_id: Optional[str] = None
    governance_decision_id: Optional[str] = None
    replay_origin_trace_id: Optional[str] = None
    retention_tier: TraceRetentionTier = TraceRetentionTier.HOT

    def close(self, status: SpanStatus, end_time: datetime) -> None:
        self.status = status
        self.end_time = end_time

    def add_event(self, event_id: str, name: str, timestamp: datetime, payload: Dict[str, Any]) -> None:
        # Prevent logging cost/narrative payloads directly
        safe_payload = {
            k: v for k, v in payload.items()
            if k not in (
                "actual_cost", "estimated_cost", "token_cost", "tokens",
                "narrative", "notes", "rationale", "assumptions", "audit_record"
            )
        }
        self.events.append(SpanEvent(event_id, name, timestamp, safe_payload))

@dataclass(frozen=True)
class TraceProjection:
    trace_id: str
    root_span: Optional[Span]
    spans: List[Span] = field(default_factory=list)
    hierarchy: Dict[str, List[str]] = field(default_factory=dict)  # parent_span_id -> child_span_ids
    is_replay: bool = False
    replay_origin_trace_id: Optional[str] = None

@dataclass(frozen=True)
class TraceQueryResult:
    trace_id: str
    projection: Optional[TraceProjection]
    lineage_span_ids: List[str] = field(default_factory=list)
    correlation_chain: List[str] = field(default_factory=dict)
