import contextvars
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable
from uuid import uuid4

from karsa.observability.domain.models import (
    Span, SpanEvent, SpanStatus, SpanKind, TraceRetentionTier,
    CorrelationContext, TraceProjection, TraceQueryResult,
    AttributionReference, DecisionJournalReference
)
from karsa.observability.domain.repositories import SpanRepository
from karsa.shared.infrastructure.uow import ConcurrencyConflictError

# Contextvars for W3C context propagation
_correlation_context: contextvars.ContextVar[CorrelationContext] = contextvars.ContextVar("correlation_context")

class W3CContextManager:
    @staticmethod
    def get_current_context() -> Optional[CorrelationContext]:
        try:
            return _correlation_context.get()
        except LookupError:
            return None

    @staticmethod
    def set_context(context: CorrelationContext) -> Any:
        return _correlation_context.set(context)

    @staticmethod
    def clear_context(token: Any) -> None:
        _correlation_context.reset(token)


class EventStreamingPlatformPort:
    """Generic Event Streaming platform abstraction port."""
    def __init__(self):
        self.subscribers: List[Callable[[Dict[str, Any], Dict[str, str]], None]] = []
        self.dlq: List[Dict[str, Any]] = []

    def publish(self, event_data: Dict[str, Any], headers: Dict[str, str]) -> None:
        # Simulate delivery
        for subscriber in self.subscribers:
            try:
                subscriber(event_data, headers)
            except Exception as e:
                # Redirect to DLQ on failure
                self.dlq.append({
                    "event_data": event_data,
                    "headers": headers,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })

    def subscribe(self, handler: Callable[[Dict[str, Any], Dict[str, str]], None]) -> None:
        self.subscribers.append(handler)


class TraceIngestionService:
    def __init__(self, repo: SpanRepository, streaming_port: EventStreamingPlatformPort):
        self.repo = repo
        self.streaming_port = streaming_port
        self.streaming_port.subscribe(self.handle_telemetry_event)

    def handle_telemetry_event(self, event_data: Dict[str, Any], headers: Dict[str, str]) -> None:
        # Extract W3C headers / correlation context
        trace_id = headers.get("trace_id") or event_data.get("trace_id")
        if not trace_id:
            raise ValueError("Telemetry event missing trace_id")

        span_id = headers.get("span_id") or event_data.get("span_id")
        if not span_id:
            raise ValueError("Telemetry event missing span_id")

        event_type = event_data.get("event_type")

        # Map correlation metadata (no raw cost or narrative values)
        context = CorrelationContext(
            trace_id=trace_id,
            workflow_id=headers.get("workflow_id") or event_data.get("workflow_id"),
            research_run_id=headers.get("research_run_id") or event_data.get("research_run_id"),
            thesis_id=headers.get("thesis_id") or event_data.get("thesis_id"),
            worker_id=headers.get("worker_id") or event_data.get("worker_id"),
            capability_execution_id=headers.get("capability_execution_id") or event_data.get("capability_execution_id"),
            provider_execution_id=headers.get("provider_execution_id") or event_data.get("provider_execution_id"),
            governance_decision_id=headers.get("governance_decision_id") or event_data.get("governance_decision_id"),
            decision_journal_id=headers.get("decision_journal_id") or event_data.get("decision_journal_id"),
            review_session_id=headers.get("review_session_id") or event_data.get("review_session_id"),
            attribution_id=headers.get("attribution_id") or event_data.get("attribution_id"),
            portfolio_id=headers.get("portfolio_id") or event_data.get("portfolio_id")
        )

        if event_type == "SpanStartedEvent":
            span = Span(
                span_id=span_id,
                trace_id=trace_id,
                name=event_data["name"],
                start_time=datetime.fromisoformat(event_data["start_time"]),
                parent_span_id=event_data.get("parent_span_id"),
                span_kind=SpanKind[event_data.get("span_kind", "INTERNAL")],
                status=SpanStatus.OK,
                tags=event_data.get("correlation_context", {}),
                review_session_id=context.review_session_id,
                governance_decision_id=context.governance_decision_id,
                replay_origin_trace_id=headers.get("replay_origin_trace_id")
            )
            # Link Attribution / Journal Reference Value Objects
            if context.attribution_id:
                span.attribution_ref = AttributionReference(context.attribution_id)
            if context.decision_journal_id:
                span.journal_ref = DecisionJournalReference(context.decision_journal_id)

            self.repo.save(span)

        elif event_type == "SpanClosedEvent":
            span = self.repo.find_by_span_id(span_id)
            if span:
                end_time = datetime.fromisoformat(event_data["end_time"])
                status = SpanStatus[event_data["status"]]
                span.close(status, end_time)
                # Map extra correlation context variables
                if context.attribution_id:
                    span.attribution_ref = AttributionReference(context.attribution_id)
                if context.decision_journal_id:
                    span.journal_ref = DecisionJournalReference(context.decision_journal_id)
                if context.review_session_id:
                    span.review_session_id = context.review_session_id
                if context.governance_decision_id:
                    span.governance_decision_id = context.governance_decision_id
                self.repo.save(span)

        elif event_type == "SpanEventLoggedEvent":
            span = self.repo.find_by_span_id(span_id)
            if span:
                timestamp = datetime.fromisoformat(event_data["timestamp"])
                span.add_event(
                    event_id=event_data["event_id"],
                    name=event_data["name"],
                    timestamp=timestamp,
                    payload=event_data.get("payload", {})
                )
                self.repo.save(span)


class SpanQueryService:
    def __init__(self, repo: SpanRepository):
        self.repo = repo

    def find_span(self, span_id: str) -> Optional[Span]:
        return self.repo.find_by_span_id(span_id)


class TraceQueryService:
    def __init__(self, repo: SpanRepository):
        self.repo = repo

    def find_trace(self, trace_id: str) -> Optional[TraceProjection]:
        spans = self.repo.find_by_trace_id(trace_id)
        if not spans:
            return None

        # Sort spans chronologically by start_time
        spans.sort(key=lambda s: s.start_time)

        # Build hierarchy (parent_span_id -> child_span_ids) and find root
        hierarchy: Dict[str, List[str]] = {}
        root_span: Optional[Span] = None
        is_replay = False
        replay_origin_trace_id = None

        for span in spans:
            if span.replay_origin_trace_id:
                is_replay = True
                replay_origin_trace_id = span.replay_origin_trace_id

            if not span.parent_span_id:
                root_span = span
            else:
                hierarchy.setdefault(span.parent_span_id, []).append(span.span_id)

        return TraceProjection(
            trace_id=trace_id,
            root_span=root_span,
            spans=spans,
            hierarchy=hierarchy,
            is_replay=is_replay,
            replay_origin_trace_id=replay_origin_trace_id
        )

    def find_lineage(self, span_id: str) -> List[Span]:
        # Walk up parent chain to construct lineage trace
        lineage: List[Span] = []
        current = self.repo.find_by_span_id(span_id)
        while current:
            lineage.append(current)
            if current.parent_span_id:
                current = self.repo.find_by_span_id(current.parent_span_id)
            else:
                break
        return lineage[::-1]  # Return chronologically root-to-leaf


class CorrelationLookupService:
    def __init__(self, repo: SpanRepository):
        self.repo = repo

    def find_traces_by_correlation(self, key: str, value: str) -> List[str]:
        spans = self.repo.find_by_correlation_key(key, value)
        # Unique list of trace IDs
        return list({span.trace_id for span in spans})

    def find_replay_origin(self, replay_trace_id: str) -> Optional[str]:
        spans = self.repo.find_by_trace_id(replay_trace_id)
        for span in spans:
            if span.replay_origin_trace_id:
                return span.replay_origin_trace_id
        return None

    def find_correlation_chain(self, trace_id: str) -> Dict[str, str]:
        # Scans spans in the trace to extract all distinct correlation keys
        spans = self.repo.find_by_trace_id(trace_id)
        chain: Dict[str, str] = {}
        for span in spans:
            # Map tag keys
            for k, v in span.tags.items():
                chain[k] = v
            # Map specific links
            if span.attribution_ref:
                chain["attribution_id"] = span.attribution_ref.attribution_id
            if span.journal_ref:
                chain["decision_journal_id"] = span.journal_ref.decision_journal_id
            if span.review_session_id:
                chain["review_session_id"] = span.review_session_id
            if span.governance_decision_id:
                chain["governance_decision_id"] = span.governance_decision_id
            if span.replay_origin_trace_id:
                chain["replay_origin_trace_id"] = span.replay_origin_trace_id
        return chain
