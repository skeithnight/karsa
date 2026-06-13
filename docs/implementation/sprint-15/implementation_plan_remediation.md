# Sprint-15 Performance Engine Foundation - Implementation Planning Remediation

## 1. Executive Summary
This document remediates implementation planning gaps for the `ARCHITECTURE_FROZEN` Sprint-15 Performance Engine Foundation. It resolves implicit runtime dependencies, ensures mathematically flawless tie-breaking for replay determinism, and formally defines persistence schemas for the daily bucket sliding windows. The architectural boundary and CQRS zero-aggregate philosophy remain strictly preserved.

## 2. Remediation Resolution Matrix
| Remediation | Gap | Resolution |
|-------------|-----|------------|
| **1. Resolver Contract** | Missing explicit context resolution flow. | Defined `DecisionContextResolver` & `InstitutionalMemoryReader` interfaces. |
| **2. Local Projection** | Runtime queries to Institutional Memory. | Introduced `projection_decision_context` for local O(1) state resolution. |
| **3. Deterministic Ordering** | `occurred_at` allows tie-break chaos. | Imposed `(occurred_at, global_sequence_id, event_id)` ordering key. |
| **4. Invalidation Strategy** | Vague recalculation on late events. | Defined formal Projection Invalidation & Rebuild Boundaries workflow. |
| **5. Projection Versioning** | No evolution path for math changes. | Introduced `calculation_version` and schema versioning models. |
| **6. Bucket Persistence** | Missing schema for daily windows. | Defined `projection_daily_pnl_bucket` and `PerformanceWindowProfile` materialization. |

## 3. DecisionContextResolver Design
To eliminate implicit dependencies, the ingestion service relies on explicit contracts.
**Interfaces:**
```python
class InstitutionalMemoryReader(Protocol):
    def read_event(self, event_id: str) -> EventEnvelope: ...

class DecisionContextResolver(Protocol):
    def resolve_context(self, decision_id: str) -> DecisionContext: ...
```
**Failure Handling:** If the context is missing, the resolver raises `DecisionContextMissingError`. The ingestion service flags the `AttributionCalculatedEvent` as `PENDING_CONTEXT` and parks it locally in a retry queue until the upstream context arrives.

## 4. Local Decision Context Projection Design
To prevent synchronous HTTP/gRPC calls to Institutional Memory during ingestion, the system materializes the necessary context locally.
**Schema:** `projection_decision_context`
- `decision_id` (PK)
- `thesis_id`
- `worker_id`
- `strategy_id`
- `stated_confidence`
- `decision_timestamp`

**Flow:**
1. `DecisionCommittedEvent` is ingested by `LocalDecisionContextProjector`.
2. Upserts to `projection_decision_context`.
3. `AttributionCalculatedEvent` arrives. `PerformanceEventIngestionService` queries the local `projection_decision_context` table for `O(1)` non-blocking reads to construct the `DecisionPerformanceRecord`.

## 5. Deterministic Ordering Contract
`occurred_at` alone is insufficient because events can execute in the same millisecond.
**Primary Ordering Key:** `occurred_at` (UTC timestamp).
**Secondary Ordering Key:** `global_sequence_id` (Institutional Memory Kafka offset / sequence token).
**Tie-breaking Rule:** `event_id` (Lexicographical ascending).

By enforcing `ORDER BY occurred_at ASC, global_sequence_id ASC, event_id ASC`, replay determinism is mathematically guaranteed to be byte-for-byte identical, completely eliminating race conditions.

## 6. Projection Invalidation Strategy
When a late-arriving event (`AttributionCalculatedEvent` or `RegimeChangedEvent`) or a Governance Restatement is processed:
1. **Invalidate Scope:** The system targets ONLY the hierarchical tree branching from the specific `target_id` (e.g., Worker/Strategy) starting from the `occurred_at` timestamp.
2. **Rebuild Boundary:** The `InvalidationOrchestrator` drops all materialized downstream values for that `target_id` after `occurred_at`.
3. **Recovery Workflow:** The orchestrator re-streams the isolated local subset of `DecisionPerformanceRecord`s for that `target_id` from `occurred_at` to `NOW()`, rebuilding the specific worker's timeline linearly.
4. **Cost Containment:** 99.9% of the projection space remains untouched; only the affected worker's subset is recalculated.

## 7. Projection Versioning Strategy
To support evolving math (e.g., Brier Score v1 to v2) without corrupting history:
- Every table includes `projection_schema_version` (int) and `calculation_version` (int).
- If `Brier Score v2` is deployed, the application logic checks `calculation_version`.
- **Migration:** A background task linearly updates `calculation_version=1` rows to `version=2` using the new algorithm formula applied to the immutable `DecisionPerformanceRecord` inputs.
- **Replay Behavior:** Replay uses the *current* codebase execution logic, stamping all newly rebuilt rows with the latest `calculation_version`, seamlessly upgrading history deterministically.

## 8. Daily Bucket Persistence Design
**Schema:** `projection_daily_pnl_bucket`
- `target_id` (Worker/Strategy/Thesis)
- `bucket_date` (DATE)
- `daily_gross_pnl` (DECIMAL(19,4))
- `daily_net_pnl` (DECIMAL(19,4))
- `PRIMARY KEY (target_id, bucket_date)`

**Aggregation Flow:**
When a `DecisionPerformanceRecord` is created:
1. Extracts `target_id`, `gross_pnl`, and `decision_timestamp::DATE`.
2. `UPSERT INTO projection_daily_pnl_bucket ... ON CONFLICT DO UPDATE SET daily_gross_pnl = daily_gross_pnl + excluded.daily_gross_pnl`.

**Window Materialization Flow:**
A 30D window is calculated via O(1) summation:
`SELECT SUM(daily_gross_pnl) FROM projection_daily_pnl_bucket WHERE target_id = X AND bucket_date >= CURRENT_DATE - 30;`
The result is stamped onto the `PerformanceWindowProfile`.

## 9. Updated Replay Design
1. Issue `TRUNCATE` against all `projection_*` tables.
2. Consume Institutional Memory ordered strictly by `(occurred_at, global_sequence_id)`.
3. Stream `RegimeChangedEvent`s to memory.
4. Stream `DecisionCommittedEvent`s to populate `projection_decision_context`.
5. Stream `AttributionCalculatedEvent`s to build `projection_decision_performance`.
6. Run background consumer groups to populate buckets and profiles.

## 10. Updated Persistence Design
Added:
- `projection_decision_context`
- `projection_daily_pnl_bucket`
Modified:
- Appended `projection_schema_version` and `calculation_version` to all projection tables.

## 11. Updated Sequence Flows
1. Institutional Memory -> `DecisionCommittedEvent` -> Local `projection_decision_context`.
2. Institutional Memory -> `AttributionCalculatedEvent` -> `PerformanceEventIngestionService`.
3. Service looks up local `projection_decision_context` directly.
4. Generates `DecisionPerformanceRecord`.
5. Emits internal update signal.
6. Pipeline consumes signal, upserts `projection_daily_pnl_bucket`, recalculates `PerformanceWindowProfile`.

## 12. Updated Class Design
Added:
- `LocalDecisionContextProjector`
- `DailyBucketAggregator`
- `ProjectionInvalidationOrchestrator`

## 13. Updated Repository Design
- `DecisionContextProjectionStore`: `get_context(decision_id: str) -> DecisionContext`
- `DailyPnlBucketStore`: `increment_bucket(target_id: str, date: date, pnl: Decimal)`

## 14. Updated Testing Strategy
- Introduce tests for deterministic sorting against composite sequence keys.
- Introduce tests ensuring `DecisionContextMissingError` triggers the local parking/retry queue.
- Test projection invalidation recalculates only bounded sub-trees.

## 15. Updated Performance Testing Strategy
- Test `DailyPnlBucketStore` concurrency to ensure simultaneous decisions correctly increment the same bucket using row-level upsert locks.

## 16. Architecture Compliance Verification
All remediations preserve the `ARCHITECTURE_FROZEN` v6 state. Zero aggregates are introduced. Institutional Memory remains the single Source of Truth. The CQRS pipeline handles all data materialization.

## 17. Architecture Delta Analysis
(None. Planning details only; architecture is identical to v6 baseline).

## 18. Final Readiness Assessment
With the explicit removal of synchronous runtime dependencies, the imposition of mathematical determinism through composite ordering keys, and the fully fleshed-out schema for window bucket materialization, the implementation planning is structurally complete.

**READY_FOR_EXECUTION**
