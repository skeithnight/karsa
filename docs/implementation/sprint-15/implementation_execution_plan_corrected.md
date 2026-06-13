# Sprint-15 Performance Engine Foundation - Corrected Implementation Execution Plan

## 1. Updated Implementation Plan
The execution of the Performance Engine Foundation strictly follows Architecture v6. This corrected plan refines the mathematical application of Identity-Aware Deltas by explicitly tracking effective generation state transitions. It corrects indexing strategies to match the concrete schema columns and details the exact cascading paths for the `ProjectionInvalidationOrchestrator`.

## 2. Updated Repository Design
**`PerformanceProjectionRepository`**:
- `append_decision_record(record: DecisionPerformanceRecord)`: Uses `INSERT ... ON CONFLICT DO NOTHING` on the composite PK `(decision_id, outcome_sequence_id, attribution_generation)`.
- `get_effective_generation_state(decision_id, outcome_sequence_id) -> Tuple[int, Decimal]`: Returns `(effective_generation_before, effective_pnl_before)`. If no rows exist, returns `(0, 0)`.
- `apply_bucket_delta(target_type, target_id, date, delta_gross, delta_net)`: UPSERTs into the `DailyPnlBucket`.

## 3. Explicit Effective Generation Transition Logic
The `IdentityAwareBucketProjector` is strictly an optimization maintainer; the bucket is never the source of truth. When an event arrives, the projector executes the following explicit generation logic:

1. Query repository for current effective state:
   `effective_generation_before, pnl_before = get_effective_generation_state(D, O)`
2. Calculate Effective Generation After:
   `effective_generation_after = MAX(effective_generation_before, incoming_generation)`
3. Calculate Delta:
   - If `incoming_generation > effective_generation_before` (Governance Restatement or Initial Event):
     `delta = incoming_pnl - pnl_before`
   - If `incoming_generation <= effective_generation_before` (Out-of-Order or Duplicate):
     `delta = 0`

**Transition Scenarios**:
- **Governance Restatement**: Incoming `Gen=2`. Before `Gen=1`. After `Gen=2`. `delta != 0`. Bucket updates, Invalidator triggers.
- **Out-of-Order Delivery**: Incoming `Gen=1` arrives late. Before `Gen=2`. After `Gen=2`. `delta = 0`. Record is appended to history, but Bucket is ignored. Invalidator does NOT trigger.
- **Duplicate Delivery**: Incoming `Gen=2` arrives again. Before `Gen=2`. After `Gen=2`. `delta = 0`. DB ignores insert via `ON CONFLICT`. Invalidator does NOT trigger.

## 4. Updated Migration Design
**Tables**: `projection_decision_performance`, `projection_daily_pnl_bucket` (polymorphic by `target_type`), plus specific profile tables.
**Corrected Index Strategy**:
The `projection_decision_performance` schema utilizes distinct foreign key columns (`worker_id`, `strategy_id`, `thesis_id`, `regime_id`). Therefore, a single "target_id" index is syntactically invalid. The migration will create specific composite indices for each dimensional slice to support lightning-fast aggregate rebuilding if needed:
- `CREATE INDEX idx_perf_worker_date ON projection_decision_performance (worker_id, decision_timestamp::DATE);`
- `CREATE INDEX idx_perf_strategy_date ON projection_decision_performance (strategy_id, decision_timestamp::DATE);`
- `CREATE INDEX idx_perf_thesis_date ON projection_decision_performance (thesis_id, decision_timestamp::DATE);`

## 5. Updated Invalidation Flow Design
When the `ProjectionInvalidationOrchestrator` receives a `delta != 0` signal at `T-minus`, it executes targeted downstream rebuilds exclusively for sequence-dependent metrics. The flow is split by profile type:

- **WorkerProfile / StrategyProfile / ThesisProfile**:
  1. `DELETE` metrics `>= T-minus` for the specific ID.
  2. Query `DailyPnlBucket` for that specific ID starting at `T-minus`.
  3. Sequentially recalculate sequence-dependent fields (e.g., Hit Rate, cumulative sums).
- **PerformanceWindowProfile**:
  1. `DELETE` windows ending `>= T-minus` for the specific ID.
  2. Slide a 30D/90D sum across the `DailyPnlBucket` to regenerate window states.
- **CalibrationProfile**:
  1. `DELETE` rows `>= T-minus` for the `(worker_id, strategy_id)` pair.
  2. Recalculate Brier Scores using corrected outcomes.
- **RegimeProfile**:
  1. Identify overlapping regimes for the worker intersecting `T-minus`.
  2. Recalculate regime-specific metrics.

## 6. Updated Test Plan
The testing suite explicitly exercises the generation transition boundaries to ensure replay determinism and idempotency.

**Expanded Replay & Ingestion Tests**:
- `test_governance_restatement_triggers_invalidation`: `Gen1` -> `Gen2` proves `delta != 0` and validates orchestrator callback.
- `test_duplicate_delivery_is_ignored`: `Gen2` -> `Gen2` proves `delta == 0` and verifies `DailyPnlBucket` is mathematically unaffected.
- `test_out_of_order_generation_is_suppressed`: `Gen3` -> `Gen2` proves `effective_generation_after == 3`, `delta == 0`, and `Gen2` is safely archived but optimization projections remain anchored to `Gen3`.
- `test_late_arrival_invalidation`: Late original event (`Gen1` arriving 3 weeks late) triggers `T-minus` rebuild spanning 3 weeks of sequence-dependent profiles.
- `test_full_database_rebuild`: Drops the entire database, replays a shuffled, duplicated, out-of-order event stream containing Governance restatements, and asserts byte-for-byte identical state to a cleanly ordered stream.
