# Sprint-49 Observability Platform Hostile Architecture Review

## 1. Executive Summary
A hostile architectural review has been performed against the proposed `57-observability-platform-design.md`. While the document cleanly scopes the read-only operational boundaries of the Observability Platform, it contains fatal contradictions regarding 10-year historical replayability versus storage pruning policies, lacks structural mitigation for metric cardinality explosions at the 1B+ event scale, and relies on passive heartbeat projections that fail to resolve "zombie worker" states conclusively. The architecture is structurally insufficient to support Sprint-50 Production Readiness limits without immediate revision.

## 2. Ownership Boundary Matrix
* **Observability Ownership**: Clean. Defined as a terminal passive sink.
* **Telemetry Ownership**: Clean. Upstream systems own the creation; Observability owns the aggregation.
* **Worker/Queue/Provider Ownership**: Clean.
**Verdict**: PASS. The God Aggregate risk is successfully avoided through pure CQRS projection bindings.

## 3. Metrics Audit
* **Cardinality Explosion**: **FAIL**. The architecture specifies `Counter`, `Gauge`, and `Histogram` models without defining tag/label cardinality limits. In a system executing millions of capabilities across distinct strategies, unrestricted capability URN tagging will collapse the time-series index.
* **High-Volume Ingestion**: **PARTIAL**. Relies on "High-throughput Time-Series compatible tables" but leaves the actual implementation (Postgres vs dedicated TSDB) undefined, masking critical latency risks.

## 4. Trace Audit
* **Trace/Correlation/Causation Propagation**: **PARTIAL**. The design mandates that upstream events include `TraceContext` (ADR-063). However, it fails to define how `TraceContext` jumps asynchronous boundaries where events are re-batched (e.g., Performance Engine aggregating multiple Outcomes before triggering Attribution).
* **Lifecycle Traceability**: **PASS**. The span hierarchy explicitly covers the mandated `Research → ... → Governance` path.

## 5. Event Observability Audit
* **Dead-letter/Retry Visibility**: **FAIL**. The architecture states Queue Observability exposes `pending`, `running`, `retrying`, and `dead_letter` counts, but fails to define how Observability links a specific dropped `EventLog` payload to its final DLQ resting state. This causes hidden event loss visibility.

## 6. Queue Audit
* **Queue Explosion**: **FAIL**. If DLQs or retry storms hit 100M+ bursts, the `QueueHealthProjectionWorker` will exhaust connection pools updating the `QueueState` snapshot synchronously for every event. Batching or debounce buffers must be specified.

## 7. Worker Audit
* **Zombie Workers & Stale Heartbeats**: **FAIL**. The architecture relies on "timeout -> OFFLINE" state transitions. However, if the Observability Platform itself lags behind the event bus, active workers will be falsely marked as offline, triggering catastrophic false-positive alerts.

## 8. Capability Audit
* **Cost / Latency / Failure Attribution**: **PASS**. The models correctly map LLM token consumption and explicit execution latency bound to the specific capability URN.

## 9. Provider Audit
* **Provider Degradation/Outage**: **PASS**. Relying on the execution workers to emit `ProviderFailed` natively captures true external API degradation boundaries.

## 10. Health Audit
* **Cascading Failures**: **FAIL**. Because the `SystemHealth` gauge is an aggregated derivative of all queues and workers, a single stuck queue could taint the global health score, masking other simultaneous independent outages.

## 11. Replayability Audit
* **10 Year Reconstruction**: **FATAL FAIL**. Section 27 (Risks) explicitly states: "100M events per day requires aggressive retention/pruning policies for raw telemetry." If raw telemetry is aggressively pruned, 10-year historical reconstruction is mathematically impossible. You cannot replay pruned data.

## 12. Scalability Audit
* **100M / 1B Events**: **FAIL**. Partitioning by `day` in PostgreSQL for 1 Billion daily events yields 30GB+ partitions per day. Querying un-indexed JSONB across 1-year of daily partitions (10TB+) for a specific `trace_id` will trigger catastrophic full table scans without an explicit inverted index (GIN/GiST) architecture.

## 13. Security Audit
* **Telemetry Tampering / Metric Poisoning**: **FAIL**. The design mentions scrubbing PII but fails to mandate cryptographic signature validation on `TraceContext` injection. A compromised worker can trivially poison the ledger by forging arbitrary `trace_ids` belonging to competing workers.

## 14. Sprint-50 Compatibility Audit
* **Production Readiness**: **FAIL**. Sprint-50 requires hardened SLAs. The reliance on pruning destroys the auditability requirement, and the lack of zombie-worker mitigation introduces unacceptable false-positive alerting vectors.

## 15. Sprint-51 Compatibility Audit
* **Research & Operations Console**: **PASS**. The snapshot-driven `OperationalStateRepository` is perfectly designed to back the sub-millisecond API demands of a frontend console.

## 16. Architecture Delta Analysis
* **Improvements**: Genuine isolation of telemetry from execution logic.
* **Hidden Complexity**: Time-series aggregation logic is vastly oversimplified.
* **Missing Capabilities**: Cryptographic telemetry validation, batch projection buffering.

## 17. Acceptance Criteria Review
* All ownership boundaries remain intact: **YES**
* Telemetry is replayable: **NO** (Pruning contradiction)
* Design scales beyond 100M events: **NO** (Missing buffering/indexing bounds)

## 18. Risks
* **Replayability Paradox**: You cannot simultaneously prune data for cost and guarantee 10-year replayability. Cold-storage offloading (e.g., S3/Parquet) must be architected.
* **Alert Fatigue**: False-positive offline states due to projection lag.

## 19. Required Remediation
1. Introduce Cold-Storage / Data Lake architecture (e.g., S3/Parquet) to preserve pruned telemetry for 10-year replayability.
2. Define explicit tag cardinality limits for the Metrics Model.
3. Introduce buffered/batched writes for the `QueueHealthProjectionWorker` to survive 1B+ retry storms.
4. Define inverted indexing requirements for Trace DB structures to prevent seq-scans.
5. Define cryptographic payload validation to prevent trace spoofing.

## 20. Final Verdict
**ARCHITECTURE_REQUIRES_REVISION**
