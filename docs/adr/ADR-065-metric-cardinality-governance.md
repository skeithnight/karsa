# ADR-065: Metric Cardinality Governance

## Status
Accepted

## Context
Observability metrics tracking high-cardinality identifiers (e.g., `thesis_urn`, `decision_urn`) structurally collapse time-series indices during metric explosions (1B+ events).

## Decision
We enforce strict classification of telemetry fields into `Metrics` vs `Events/Traces`.
* **Prohibited Metric Labels**: `thesis_urn`, `decision_urn`, `worker_urn` (if >1000 workers), `trace_id`.
* **Allowed Metric Labels**: `capability_type`, `provider_id`, `queue_name`, `status_code`.

High-cardinality values may ONLY be embedded as properties inside `EventLog` or `TraceSpan` payloads, which are inherently indexed differently (e.g., GIN indexing on JSONB or structured columnar) and do not participate in real-time Time-Series aggregations.

## Consequences
* Protects the metric aggregation layer from OOM and index bloat.
* Limits the ability to query "metrics by specific thesis" in real-time dashboards; such queries must hit the Trace Database instead.
