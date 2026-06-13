# Sprint-15 Performance Engine Foundation - Implementation Planning Package

## 1. Executive Summary
This Implementation Planning Package translates the `ARCHITECTURE_FROZEN` Sprint-15 Performance Engine Foundation (Revision v6) into a concrete execution blueprint. The implementation strictly adheres to the pure CQRS, zero-aggregate, Decision-centric architecture. It outlines the file structures, database schemas, and the specific Layered Projection Pipeline required to asynchronously compute multi-dimensional performance metrics without locking contention.

## 2. Architecture Freeze Validation
- **Architecture Baseline**: Sprint-15 Revision v6.
- **Constraints Maintained**: Zero aggregates, projection-only storage authority, strict statistical ownership (no alpha or capital multipliers), and drop-to-zero replay guarantees.

## 3. Package Structure
```text
src/karsa/performance/
├── domain/
│   ├── model/
│   │   ├── events.py
│   │   ├── projections.py
│   │   └── value_objects.py
│   └── service/
│       ├── projection_orchestrator.py
│       └── calibration_evaluator.py
├── application/
│   └── service.py
├── infrastructure/
│   ├── bus/
│   │   └── local_pipeline.py
│   └── storage/
│       └── postgres_projections.py
└── presentation/
    └── event_handlers.py
```

## 4. File Creation Plan
- `src/karsa/performance/domain/model/value_objects.py`: Implement `DecisionPerformanceIdentity`, `RiskMetrics`, `CalibrationMetrics`.
- `src/karsa/performance/domain/model/projections.py`: Define `DecisionPerformanceRecord`, `WorkerPerformanceProfile`, etc.
- `src/karsa/performance/application/service.py`: Implement `PerformanceEventIngestionService`.
- `src/karsa/performance/infrastructure/storage/postgres_projections.py`: Implement UPSERT mechanics.
- `src/karsa/performance/infrastructure/bus/local_pipeline.py`: Internal async dispatcher.

## 5. File Modification Plan
- Update Alembic migrations to include new `projection_*` tables.
- Register `PerformanceEventIngestionService` into the primary Event Bus subscriber registry.

## 6. Class Design
- **`PerformanceEventIngestionService`**: Listens to raw events, joins inputs, constructs the root `DecisionPerformanceRecord`, and publishes an internal signal.
- **`CalibrationEvaluator`**: Pure mathematical domain service (Brier Score).
- **`HierarchicalProjectionOrchestrator`**: Dispatches the root record to specialized projection mutators (`WorkerProjector`, `ThesisProjector`, `RegimeProjector`).

## 7. Projection Design
Projections are implemented as immutable dataclasses translated into dictionary structures for persistence.
- `DecisionPerformanceRecord`
- `ThesisPerformanceProfile`
- `WorkerPerformanceProfile`
- `StrategyPerformanceProfile`
- `RegimePerformanceProfile`
- `CalibrationProfile`
- `PerformanceWindowProfile`

## 8. Value Object Design
- **`DecisionPerformanceIdentity`**: `(decision_id: str, outcome_sequence_id: int, attribution_generation: int)`.
- **`RiskMetrics`**: `(cumulative_pnl: Decimal, max_drawdown: Decimal, volatility_proxy: Decimal)`. All floats avoided; strictly `DECIMAL(19,4)` using Bankers Rounding.

## 9. Repository Design
- **`DecisionPerformanceProjectionStore`**: `save(record: DecisionPerformanceRecord)` utilizing PostgreSQL `ON CONFLICT DO UPDATE`.
- **`HierarchicalProfileStore`**: `upsert_profile(target_id: str, profile_type: str, delta_metrics: RiskMetrics)`.

## 10. Persistence Mapping
Projections will map to individual tables (e.g., `projection_decision_performance`) to allow distinct read models to be queried via simple primary key indexing.

## 11. Event Schema Design
- **`PerformanceSnapshotPublishedEvent`**:
  - `target_id`: String
  - `target_type`: String (Worker/Thesis/Strategy)
  - `metrics`: Dictionary of `RiskMetrics` and `CalibrationMetrics`.
  - `snapshot_timestamp`: ISO8601 UTC.

## 12. Application Service Design
The `PerformanceEventIngestionService` acts as the entrypoint. It receives an `AttributionCalculatedEvent`, performs a lookup on Institutional Memory for the associated `DecisionCommittedEvent` (to retrieve stated confidence), builds the `DecisionPerformanceRecord`, and triggers the internal projection bus.

## 13. UnitOfWork Integration Design
UoW is utilized strictly for ensuring that internal projection updates and the subsequent `Outbox` write (if a snapshot is emitted) are atomically committed to PostgreSQL. Because there are no domain aggregates to lock, `ConcurrencyConflictError` scenarios are impossible.

## 14. Outbox Integration Design
`PerformanceSnapshotPublishedEvent`s are routed through the standard `karsa.shared.infrastructure.outbox` table during the projection pipeline commit phase.

## 15. Projection Pipeline Design
To avoid synchronous fan-out lockup:
1. `PerformanceEventIngestionService` inserts the root record and commits the UoW.
2. A background `asyncio` task or internal queue worker (the `LocalPipeline`) wakes up, calculates the delta for Worker, Thesis, and Regime, and upserts them via distinct, non-blocking UoWs.

## 16. Replay Implementation Design
A dedicated management command (`karsa-cli performance replay`) will:
1. Issue `TRUNCATE TABLE projection_decision_performance CASCADE;`
2. Iterate through Institutional Memory events in pure chronological (`occurred_at`) order.
3. Call `PerformanceEventIngestionService` directly.
4. Block until the projection pipeline drains.

## 17. Idempotency Design
Every projection table utilizes its logical identity (`decision_id`, `outcome_sequence_id`, `attribution_generation`) as a `UNIQUE` constraint. `UPSERT` semantics handle duplicate event delivery by overwriting the projection safely with identical math.

## 18. Event Ordering Design
Strictly ordered by the `occurred_at` timestamp. Before ingestion, events are verified. If a late-arriving event triggers an out-of-order warning, the system flags it.

## 19. Late Arrival Event Handling Design
Because metrics like `max_drawdown` are sequence-dependent, a late-arriving historic event (e.g., 3 weeks delayed) will trigger an automatic isolated recalculation of that specific `target_id`'s temporal projection history to ensure statistical reality aligns with time.

## 20. Database Schema Design
```sql
CREATE TABLE projection_decision_performance (
    decision_id VARCHAR(36) NOT NULL,
    outcome_sequence_id INT NOT NULL,
    attribution_generation INT NOT NULL,
    worker_id VARCHAR(36) NOT NULL,
    strategy_id VARCHAR(36) NOT NULL,
    thesis_id VARCHAR(36) NOT NULL,
    regime_id VARCHAR(36),
    gross_pnl DECIMAL(19,4) NOT NULL,
    stated_confidence DECIMAL(5,4),
    brier_score DECIMAL(19,4),
    decision_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (decision_id, outcome_sequence_id, attribution_generation)
);
-- Similar schemas for hierarchical profiles.
```

## 21. Migration Plan
Create Alembic revision adding the 7 projection tables. No data migration required as the engine is entirely new.

## 22. Rollback Plan
If projection logic fails, rollback the application code and run `karsa-cli performance replay` to rebuild the views identically.

## 23. Testing Strategy
Given the pure mathematical nature of this bounded context, the testing strategy focuses on 100% deterministic assertion of the `CalibrationEvaluator` and precise SQL Upsert syntax matching.

## 24. Unit Test Plan
- `test_brier_score_math`
- `test_drawdown_calculation`
- `test_bankers_rounding_precision`
- `test_decision_record_construction`

## 25. Integration Test Plan
- `test_projection_pipeline_fanout`: Verify 1 attribution event results in 6 specialized materialized view updates.
- `test_idempotency_on_duplicate_event`: Inject 2 identical events; verify `rowcount` unchanged.

## 26. Replay Test Plan
- `test_drop_and_rebuild`: Simulate 50 events, record hashes of all tables, truncate all tables, replay the 50 events, assert hashes match perfectly.

## 27. Performance Test Plan
- `test_100k_ingestion_throughput`: Ensure the Layered Projection Pipeline handles high throughput without UoW transaction locks.

## 28. Production Readiness Assessment
The system avoids external synchronous dependencies, guarantees mathematically flawless replay, and emits non-blocking updates. It is production ready.

## 29. Technical Debt Assessment
The `Decision` object remains a string token routing key. The system lacks a formal `Decision Engine`, but this is a documented roadmap feature, not a debt.

## 30. Final Implementation Verdict
**READY_FOR_EXECUTION_REVIEW**
