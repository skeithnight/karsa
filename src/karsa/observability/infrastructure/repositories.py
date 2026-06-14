import copy
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
from karsa.observability.domain.models import Span
from karsa.observability.domain.repositories import SpanRepository
from karsa.shared.infrastructure.uow import ConcurrencyConflictError

class InMemorySpanRepository(SpanRepository):
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}

    def _serialize(self, span: Span) -> Dict[str, Any]:
        events_serialized = []
        for e in span.events:
            events_serialized.append({
                "event_id": e.event_id,
                "name": e.name,
                "timestamp": e.timestamp.isoformat(),
                "payload": copy.deepcopy(e.payload)
            })
        return {
            "span_id": span.span_id,
            "trace_id": span.trace_id,
            "name": span.name,
            "start_time": span.start_time.isoformat(),
            "parent_span_id": span.parent_span_id,
            "span_kind": span.span_kind.name,
            "status": span.status.name,
            "end_time": span.end_time.isoformat() if span.end_time else None,
            "events": events_serialized,
            "tags": copy.deepcopy(span.tags),
            "attribution_id": span.attribution_ref.attribution_id if span.attribution_ref else None,
            "decision_journal_id": span.journal_ref.decision_journal_id if span.journal_ref else None,
            "review_session_id": span.review_session_id,
            "governance_decision_id": span.governance_decision_id,
            "replay_origin_trace_id": span.replay_origin_trace_id,
            "retention_tier": span.retention_tier.name,
            "aggregate_version": span.aggregate_version
        }

    def _deserialize(self, data: Dict[str, Any]) -> Span:
        from karsa.observability.domain.models import (
            SpanEvent, SpanKind, SpanStatus, TraceRetentionTier,
            AttributionReference, DecisionJournalReference
        )
        events = []
        for e in data["events"]:
            events.append(SpanEvent(
                event_id=e["event_id"],
                name=e["name"],
                timestamp=datetime.fromisoformat(e["timestamp"]),
                payload=copy.deepcopy(e["payload"])
            ))
        span = Span(
            span_id=data["span_id"],
            trace_id=data["trace_id"],
            name=data["name"],
            start_time=datetime.fromisoformat(data["start_time"]),
            parent_span_id=data["parent_span_id"],
            span_kind=SpanKind[data["span_kind"]],
            status=SpanStatus[data["status"]],
            end_time=datetime.fromisoformat(data["end_time"]) if data["end_time"] else None,
            events=events,
            tags=copy.deepcopy(data["tags"]),
            review_session_id=data["review_session_id"],
            governance_decision_id=data["governance_decision_id"],
            replay_origin_trace_id=data["replay_origin_trace_id"],
            retention_tier=TraceRetentionTier[data["retention_tier"]]
        )
        if data.get("attribution_id"):
            span.attribution_ref = AttributionReference(data["attribution_id"])
        if data.get("decision_journal_id"):
            span.journal_ref = DecisionJournalReference(data["decision_journal_id"])
        span.aggregate_version = data["aggregate_version"]
        return span

    def save(self, span: Span) -> None:
        if span.span_id in self._data:
            stored = self._data[span.span_id]
            stored_version = stored["aggregate_version"]
            # OCC checks: stored version must equal input version minus 1
            if stored_version != span.aggregate_version and stored_version != span.aggregate_version - 1:
                raise ConcurrencyConflictError(f"Concurrency conflict saving Span {span.span_id}")
            span.aggregate_version = stored_version + 1
        else:
            span.aggregate_version = 1
        self._data[span.span_id] = self._serialize(span)

    def save_batch(self, spans: List[Span]) -> None:
        for span in spans:
            self.save(span)

    def find_by_span_id(self, span_id: str) -> Optional[Span]:
        if span_id not in self._data:
            return None
        return self._deserialize(self._data[span_id])

    def find_by_trace_id(self, trace_id: str) -> List[Span]:
        results = []
        for span_id, data in self._data.items():
            if data["trace_id"] == trace_id:
                results.append(self._deserialize(data))
        return results

    def find_by_correlation_key(self, key: str, value: str) -> List[Span]:
        results = []
        for span_id, data in self._data.items():
            # Check tag value or explicit correlation key
            if data.get(key) == value or data.get("tags", {}).get(key) == value:
                results.append(self._deserialize(data))
        return results

    def prune_older_than_days(self, days: int) -> int:
        now = datetime.utcnow()
        to_delete = []
        for span_id, data in self._data.items():
            start_time = datetime.fromisoformat(data["start_time"])
            if (now - start_time).days > days:
                to_delete.append(span_id)
        for span_id in to_delete:
            del self._data[span_id]
        return len(to_delete)


class FileSpanRepository(SpanRepository):
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.base_dir = self.workspace_path / ".karsa" / "observability" / "spans"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._mem = InMemorySpanRepository()

    def _get_file_path(self, span_id: str) -> Path:
        return self.base_dir / f"{span_id}.json"

    def save(self, span: Span) -> None:
        file_path = self._get_file_path(span.span_id)
        if file_path.exists():
            with open(file_path, "r") as f:
                stored = json.load(f)
            stored_version = stored["aggregate_version"]
            if stored_version != span.aggregate_version and stored_version != span.aggregate_version - 1:
                raise ConcurrencyConflictError(f"Concurrency conflict saving Span {span.span_id} to file")
            span.aggregate_version = stored_version + 1
        else:
            span.aggregate_version = 1

        serialized = self._mem._serialize(span)
        # Atomically write file
        temp_file = file_path.with_suffix(".tmp")
        with open(temp_file, "w") as f:
            json.dump(serialized, f, indent=4)
        temp_file.replace(file_path)

    def save_batch(self, spans: List[Span]) -> None:
        for span in spans:
            self.save(span)

    def find_by_span_id(self, span_id: str) -> Optional[Span]:
        file_path = self._get_file_path(span_id)
        if not file_path.exists():
            return None
        with open(file_path, "r") as f:
            data = json.load(f)
        return self._mem._deserialize(data)

    def find_by_trace_id(self, trace_id: str) -> List[Span]:
        results = []
        for file in self.base_dir.glob("*.json"):
            with open(file, "r") as f:
                data = json.load(f)
            if data["trace_id"] == trace_id:
                results.append(self._mem._deserialize(data))
        return results

    def find_by_correlation_key(self, key: str, value: str) -> List[Span]:
        results = []
        for file in self.base_dir.glob("*.json"):
            with open(file, "r") as f:
                data = json.load(f)
            if data.get(key) == value or data.get("tags", {}).get(key) == value:
                results.append(self._mem._deserialize(data))
        return results

    def prune_older_than_days(self, days: int) -> int:
        now = datetime.utcnow()
        count = 0
        for file in self.base_dir.glob("*.json"):
            with open(file, "r") as f:
                data = json.load(f)
            start_time = datetime.fromisoformat(data["start_time"])
            if (now - start_time).days > days:
                file.unlink()
                count += 1
        return count
