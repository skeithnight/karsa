import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import pytest

from karsa.observability.domain.models import (
    Span, SpanEvent, SpanStatus, SpanKind, TraceRetentionTier,
    CorrelationContext, AttributionReference, DecisionJournalReference
)
from karsa.observability.domain.events import (
    SpanStartedEvent, SpanClosedEvent, SpanEventLoggedEvent
)
from karsa.observability.application.services import (
    W3CContextManager, EventStreamingPlatformPort, TraceIngestionService,
    SpanQueryService, TraceQueryService, CorrelationLookupService
)
from karsa.observability.infrastructure.repositories import (
    InMemorySpanRepository, FileSpanRepository
)
from karsa.shared.infrastructure.uow import ConcurrencyConflictError


def test_span_lifecycle():
    # Span started
    start = datetime.utcnow()
    span = Span(
        span_id="span_1",
        trace_id="trace_1",
        name="test_operation",
        start_time=start,
        span_kind=SpanKind.INTERNAL,
        status=SpanStatus.OK
    )
    assert span.status == SpanStatus.OK
    assert span.end_time is None

    # Add event (verify cost/narrative payloads are stripped)
    span.add_event(
        event_id="evt_1",
        name="something_happened",
        timestamp=start + timedelta(seconds=1),
        payload={
            "ok_key": "val",
            "actual_cost": 0.05,        # Prohibited - should be stripped
            "narrative": "explaining why"  # Prohibited - should be stripped
        }
    )
    assert len(span.events) == 1
    event = span.events[0]
    assert event.payload["ok_key"] == "val"
    assert "actual_cost" not in event.payload
    assert "narrative" not in event.payload

    # Close span
    end = start + timedelta(seconds=5)
    span.close(SpanStatus.ERROR, end)
    assert span.status == SpanStatus.ERROR
    assert span.end_time == end


def test_occ_concurrency_conflict():
    repo = InMemorySpanRepository()
    span = Span(
        span_id="span_1",
        trace_id="trace_1",
        name="test_operation",
        start_time=datetime.utcnow()
    )
    repo.save(span)
    assert span.aggregate_version == 1

    # Save same instance again (correct increment)
    repo.save(span)
    assert span.aggregate_version == 2

    # Simulate stale write by manually modifying the saved version
    span.aggregate_version = 1
    with pytest.raises(ConcurrencyConflictError):
        repo.save(span)


def test_w3c_context_propagation():
    context = CorrelationContext(
        trace_id="trace_123",
        workflow_id="wf_999",
        research_run_id="res_777",
        thesis_id="thesis_888"
    )

    # Set context
    token = W3CContextManager.set_context(context)
    current = W3CContextManager.get_current_context()
    assert current is not None
    assert current.trace_id == "trace_123"
    assert current.workflow_id == "wf_999"

    # Clear context
    W3CContextManager.clear_context(token)
    assert W3CContextManager.get_current_context() is None


def test_event_ingestion_and_query():
    repo = InMemorySpanRepository()
    port = EventStreamingPlatformPort()
    service = TraceIngestionService(repo, port)

    # Start event
    port.publish({
        "event_type": "SpanStartedEvent",
        "trace_id": "trace_w3c",
        "span_id": "span_w3c_1",
        "name": "w3c_span",
        "start_time": "2026-06-14T05:00:00",
        "parent_span_id": None,
        "span_kind": "SERVER",
        "correlation_context": {"workflow_id": "wf_1"}
    }, headers={
        "trace_id": "trace_w3c",
        "span_id": "span_w3c_1",
        "workflow_id": "wf_1",
        "attribution_id": "attr_101",
        "decision_journal_id": "jrn_202"
    })

    # Assert span exists
    span = repo.find_by_span_id("span_w3c_1")
    assert span is not None
    assert span.name == "w3c_span"
    assert span.span_kind == SpanKind.SERVER
    assert span.attribution_ref is not None
    assert span.attribution_ref.attribution_id == "attr_101"
    assert span.journal_ref is not None
    assert span.journal_ref.decision_journal_id == "jrn_202"

    # Log event inside span
    port.publish({
        "event_type": "SpanEventLoggedEvent",
        "trace_id": "trace_w3c",
        "span_id": "span_w3c_1",
        "event_id": "sub_evt_1",
        "name": "checkpoint",
        "timestamp": "2026-06-14T05:00:02",
        "payload": {"checkpoint_num": 1}
    }, headers={"trace_id": "trace_w3c", "span_id": "span_w3c_1"})

    # Closed event
    port.publish({
        "event_type": "SpanClosedEvent",
        "trace_id": "trace_w3c",
        "span_id": "span_w3c_1",
        "end_time": "2026-06-14T05:00:10",
        "status": "OK"
    }, headers={"trace_id": "trace_w3c", "span_id": "span_w3c_1"})

    span = repo.find_by_span_id("span_w3c_1")
    assert span.status == SpanStatus.OK
    assert span.end_time == datetime(2026, 6, 14, 5, 0, 10)
    assert len(span.events) == 1
    assert span.events[0].name == "checkpoint"


def test_trace_projection_and_lineage():
    repo = InMemorySpanRepository()
    
    # Trace 1
    now = datetime.utcnow()
    s1 = Span(span_id="span_root", trace_id="trace_1", name="root", start_time=now, parent_span_id=None)
    s2 = Span(span_id="span_child_1", trace_id="trace_1", name="child_1", start_time=now + timedelta(seconds=1), parent_span_id="span_root")
    s3 = Span(span_id="span_child_2", trace_id="trace_1", name="child_2", start_time=now + timedelta(seconds=2), parent_span_id="span_root")
    s4 = Span(span_id="span_grandchild", trace_id="trace_1", name="grandchild", start_time=now + timedelta(seconds=3), parent_span_id="span_child_1")
    repo.save_batch([s1, s2, s3, s4])

    query = TraceQueryService(repo)
    trace = query.find_trace("trace_1")
    assert trace is not None
    assert trace.root_span.span_id == "span_root"
    assert len(trace.spans) == 4
    assert "span_root" in trace.hierarchy
    assert "span_child_1" in trace.hierarchy["span_root"]
    assert "span_child_2" in trace.hierarchy["span_root"]
    assert "span_grandchild" in trace.hierarchy["span_child_1"]

    # Lineage reconstruction
    lineage = query.find_lineage("span_grandchild")
    assert len(lineage) == 3
    assert [s.span_id for s in lineage] == ["span_root", "span_child_1", "span_grandchild"]


def test_correlation_lookup_and_replay():
    repo = InMemorySpanRepository()
    now = datetime.utcnow()
    
    s1 = Span(span_id="s1", trace_id="t1", name="op1", start_time=now)
    s1.attribution_ref = AttributionReference("attr_999")
    s1.tags = {"thesis_id": "thesis_xyz"}
    s1.review_session_id = "rev_session_1"
    
    # Replay trace
    s2 = Span(span_id="s2", trace_id="t2_replay", name="op1", start_time=now)
    s2.replay_origin_trace_id = "t1"
    
    repo.save_batch([s1, s2])

    lookup = CorrelationLookupService(repo)
    
    # Find traces by correlation
    traces = lookup.find_traces_by_correlation("thesis_id", "thesis_xyz")
    assert "t1" in traces

    # Find replay origin
    origin = lookup.find_replay_origin("t2_replay")
    assert origin == "t1"

    # Find correlation chain
    chain = lookup.find_correlation_chain("t1")
    assert chain["attribution_id"] == "attr_999"
    assert chain["thesis_id"] == "thesis_xyz"
    assert chain["review_session_id"] == "rev_session_1"


def test_file_repository_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        repo = FileSpanRepository(workspace)

        now = datetime.utcnow()
        span = Span(
            span_id="f_span_1",
            trace_id="f_trace_1",
            name="file_operation",
            start_time=now
        )
        repo.save(span)

        # Retrieve file
        retrieved = repo.find_by_span_id("f_span_1")
        assert retrieved is not None
        assert retrieved.name == "file_operation"
        assert retrieved.aggregate_version == 1

        # Save again (OCC verify)
        retrieved.name = "file_operation_updated"
        repo.save(retrieved)
        
        updated = repo.find_by_span_id("f_span_1")
        assert updated.name == "file_operation_updated"
        assert updated.aggregate_version == 2


def test_retention_pruning():
    repo = InMemorySpanRepository()
    now = datetime.utcnow()
    
    # 40 days old span
    s1 = Span(span_id="old_span", trace_id="t1", name="op", start_time=now - timedelta(days=40))
    s2 = Span(span_id="new_span", trace_id="t2", name="op", start_time=now - timedelta(days=5))
    repo.save_batch([s1, s2])

    pruned = repo.prune_older_than_days(30)
    assert pruned == 1
    assert repo.find_by_span_id("old_span") is None
    assert repo.find_by_span_id("new_span") is not None
