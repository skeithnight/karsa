# Sprint-15 Performance Engine Foundation - Implementation Execution Plan

## 1. Implementation Plan
The execution of the Performance Engine Foundation adheres strictly to the frozen Architecture v6 blueprint. The development is split into three phases:
- **Phase 1**: Persistence layer schema creation (Alembic) and basic models.
- **Phase 2**: Event ingestion, local `projection_decision_context` construction, and `projection_decision_performance` append-only logic.
- **Phase 3**: Identity-Aware Contribution delta application, `DailyPnlBucket` optimization, and `ProjectionInvalidationOrchestrator` cascading rebuilds.

## 2. File Creation Matrix
| File Path | Description |
|-----------|-------------|
| `src/karsa/performance/domain/events.py` | DLQ and snapshot event schemas. |
| `src/karsa/performance/domain/value_objects.py` | `DecisionPerformanceIdentity`, `RiskMetrics`. |
| `src/karsa/performance/domain/projections.py` | Dataclasses for all `Profile` schemas. |
| `src/karsa/performance/application/ingestion.py` | `PerformanceEventIngestionService`. |
| `src/karsa/performance/application/orchestration.py` | `ProjectionInvalidationOrchestrator`. |
| `src/karsa/performance/infrastructure/repositories.py` | `PerformanceProjectionRepository`. |
| `src/karsa/performance/presentation/cli.py` | `karsa-cli performance replay`. |

## 3. File Modification Matrix
| File Path | Description |
|-----------|-------------|
| `alembic/versions/..._performance_projections.py` | Migration adding 8 tables and 1 view. |
| `src/karsa/shared/infrastructure/bus.py` | Register performance event handlers. |

## 4. Class Designs
- **`PerformanceEventIngestionService`**: Listens to `AttributionCalculatedEvent`. Fetches context. Handles `DecisionContextMissingError` by dropping to DLQ after 5 retries.
- **`IdentityAwareBucketProjector`**: Fetches MAX generation for `(decision_id, outcome_seq_id)`. Computes `delta`.
- **`ProjectionInvalidationOrchestrator`**: Receives internal `delta != 0` signal. Drops affected `target_id` sequence-dependent profiles `>= occurred_at`. Re-runs calculations.
- **`PerformanceReplayEngine`**: Drops schema, streams Institutional Memory via composite sort.

## 5. Repository Designs
- **`DecisionContextProjectionStore`**: `save_context()`, `get_context()`.
- **`PerformanceProjectionRepository`**: 
  - `append_decision_record()` (Insert only, ignores constraint violations).
  - `get_highest_generation_pnl(decision, outcome) -> Decimal`.
  - `apply_bucket_delta(target, date, delta_gross, delta_net)`.
  - `get_bucket_stream(target, start_date) -> Iterator[Bucket]`.

## 6. Alembic Migration Design
- **Tables**: `projection_decision_context`, `projection_decision_performance`, `projection_daily_pnl_bucket`, `projection_worker_performance`, `projection_strategy_performance`, `projection_thesis_performance`, `projection_regime_performance`, `projection_calibration`, `projection_performance_window`.
- **Constraints**: Composite PK on `decision_performance` = `(decision_id, outcome_sequence_id, attribution_generation)`.
- **Indices**: Composite index on `decision_performance` = `(target_id, DATE(decision_timestamp))` for rapid aggregation.
- **View**: `CREATE VIEW view_ranking_profile AS SELECT worker_id, RANK() OVER (ORDER BY sharpe_proxy DESC) as rank FROM projection_worker_performance`.

## 7. Event Handler Design
1. `DecisionCommittedEvent` -> `upsert_decision_context`.
2. `AttributionCalculatedEvent` -> `PerformanceEventIngestionService` ->
   - Retrieve context.
   - Lookup `prior_pnl` from `projection_decision_performance`.
   - `delta = new_pnl - prior_pnl`.
   - Append to `projection_decision_performance`.
   - If `delta != 0`: `apply_bucket_delta`, trigger `ProjectionInvalidationOrchestrator`.

## 8. Replay Command Design
`karsa-cli performance replay`
- Executes `TRUNCATE TABLE projection_decision_performance CASCADE`.
- Streams events with `ORDER BY occurred_at ASC, global_sequence_id ASC, event_id ASC`.
- Bypasses DLQ (context is guaranteed to exist chronologically).

## 9. Invalidation Flow Design
When `ProjectionInvalidationOrchestrator` receives a rebuild signal for `target_id` at `T-minus`:
1. `DELETE FROM projection_performance_window WHERE target_id = X AND window_end >= T-minus`.
2. Fetch `DailyPnlBucket` stream from `T-minus` -> NOW.
3. Compute rolling Max Drawdown sequentially.
4. Materialize updated profiles.

## 10. Unit Tests
- `test_identity_aware_delta_calculation`: Verifies duplicate generations yield delta 0.
- `test_out_of_order_generation_yields_zero_delta`: Verifies Gen2 arriving after Gen3 yields delta 0.
- `test_brier_score_math`: Pure math test.

## 11. Integration Tests
- `test_ingestion_pipeline_end_to_end`: From Kafka mock to `DailyPnlBucket` and `WindowProfile`.
- `test_dlq_routing_on_missing_context`: Verifies exactly 5 retries before routing to DLQ.
- `test_query_time_ranking_view`: Verifies `RANK() OVER` updates dynamically.

## 12. Replay Tests
- `test_deterministic_rebuild`: Simulate 1,000 randomized events. Drop DB. Rebuild. Hash DB schema. Assert hashes match.

## 13. Performance Tests
- `test_bucket_delta_upsert_scale`: Benchmark 10,000 delta applications per second to verify row-lock isolation on the bucket table.

## 14. Production Readiness Verification
The design requires NO synchronous network calls to Institutional Memory during ingestion, gracefully handles missing context via DLQ, prevents read-amplification via the Identity-Aware Delta, and relies on Postgres Views for global ranking. It is perfectly aligned with `EXECUTION_APPROVED` constraints.
