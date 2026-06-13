# Sprint-13 Performance Engine Foundation - Implementation Planning Package

## 1. Executive Summary
This document provides the exhaustive implementation blueprint for the Sprint-13 Performance Engine Foundation. The architecture is formally frozen. This plan dictates the strict code structures, application flows, database schemas, and testing strategies required to implement the `PerformanceProfileWindow` aggregate, the stateless `ThesisEvaluationService`, the explicit `MetricRegistry`, and the `PerformanceFanOutSaga`. Implementation execution must adhere to this document exactly, preserving all Sprint-11.5 and Sprint-12 foundation constraints.

## 2. Architecture Freeze Validation
- **Status**: ARCHITECTURE_FROZEN.
- **Constraints Checked**: No new bounded contexts, no knowledge graphs, no redesigns.
- **Foundation Checked**: Single Aggregate UoW, OCC, Outbox, and PlatformEventEnvelope constraints perfectly preserved.

## 3. Package Structure
```text
src/karsa/performance/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── model/
│   │   ├── __init__.py
│   │   ├── profile.py
│   │   ├── evaluation.py
│   │   └── value_objects.py
│   └── registry/
│       ├── __init__.py
│       └── metric_registry.py
├── application/
│   ├── __init__.py
│   ├── commands.py
│   ├── service/
│   │   ├── __init__.py
│   │   └── performance_application_service.py
│   └── saga/
│       ├── __init__.py
│       └── fanout_saga.py
├── infrastructure/
│   ├── __init__.py
│   └── storage/
│       ├── __init__.py
│       ├── profile_mapper.py
│       └── profile_repository.py
└── events/
    ├── __init__.py
    └── performance_events.py
```

## 4. File Creation Plan
- `src/karsa/performance/domain/model/profile.py`: `PerformanceProfileWindow` Aggregate.
- `src/karsa/performance/domain/model/evaluation.py`: `ThesisEvaluationService` Domain Service.
- `src/karsa/performance/domain/registry/metric_registry.py`: Formula definitions.
- `src/karsa/performance/application/saga/fanout_saga.py`: FanOut routing.
- `src/karsa/performance/infrastructure/storage/profile_repository.py`: Postgres OCC implementation.

## 5. File Modification Plan
- Add `PerformanceMetrics` structures to shared domain if needed, else scope tightly within `karsa.performance`.

## 6. Class Design
- **`PerformanceProfileWindow`**: Inherits `VersionedAggregate`.
- **`ThesisEvaluationService`**: Stateless logic class.
- **`MetricRegistry`**: Singleton/Module-level static definition registrar.
- **`PerformanceApplicationService`**: UoW coordinator.
- **`PerformanceFanOutSaga`**: Event subscriber.

## 7. Aggregate Implementation Design
**`PerformanceProfileWindow`**
- **Fields**: `target_identity` (VO), `window_identity` (VO), `prediction_metrics` (VO), `investment_metrics` (VO).
- **Methods**: `apply_evaluation_grade(grade: EvaluationGrade)`.
- **Invariants**: Must not allow negative counts. `brier_score` must remain 0.0-1.0.
- **Versioning**: `self.increment_version()` on every metric bump.
- **Window Ownership**: Strictly bound to one specific Time Window (e.g., "2026-Q3").
- **State Mutation**: Overwrites metric properties entirely with newly computed values from `MetricRegistry`.

## 8. Value Object Implementation Design
- **`TargetIdentity`**: `target_id: str`, `target_type: str` (ORIGINATOR | WORKER | STRATEGY).
- **`WindowIdentity`**: `period_type: str` (MONTH | QUARTER), `period_value: str` (e.g. "2026-06").
- **`PredictionMetrics`**: `@dataclass(frozen=True)` containing `hit_rate`, `brier_score`, `evaluation_count`.
- **`InvestmentMetrics`**: `@dataclass(frozen=True)` containing `average_roi`, `capital_efficiency_score`.
- **`EvaluationGrade`**: `@dataclass(frozen=True)` containing `prediction_score`, `investment_score`, `timing_score`.
- **`ThesisScoreRecord`**: `@dataclass(frozen=True)` tracking thesis_id and impact.

## 9. Repository Design
```python
class ProfileRepository(ABC):
    @abstractmethod
    def get_by_identity(self, target: TargetIdentity, window: WindowIdentity) -> PerformanceProfileWindow | None: ...
    @abstractmethod
    def save(self, profile: PerformanceProfileWindow) -> None: ...
```

## 10. Persistence Mapping Design
`ProfileMapper` explicitly dumps `TargetIdentity`, `WindowIdentity`, `PredictionMetrics`, and `InvestmentMetrics` directly into a single flat `JSONB` column. 

## 11. Event Schema Design
- **`ThesisEvaluatedPayload`**: `thesis_id`, `evaluation_grade`, `metric_version`, `algorithm_hash`, `evaluated_at`.
- **`PerformanceProfileUpdatedPayload`**: `target_identity`, `window_identity`, `prediction_metrics`, `investment_metrics`, `update_reason` (which thesis_id triggered this).

## 12. Command Model Design
- `EvaluateThesisCommand`: `thesis_id`, `actual_outcome`, `resolution_date`.
- `ApplyEvaluationCommand`: `target_identity`, `window_identity`, `evaluation_grade`.
- `RebuildPerformanceProfilesCommand`: Admin command for system rebuilds.

## 13. Application Service Design
`PerformanceApplicationService`:
- `evaluate_thesis()`: Loads `ThesisContextSnapshot` (simulated via API or retrieved), calls `ThesisEvaluationService`, stages `ThesisEvaluatedEvent`.
- `apply_evaluation_to_profile()`: Opens UoW. `repo.get_by_identity()`. If None, create new window. `profile.apply_evaluation_grade()`. Save. Stage `PerformanceProfileUpdatedEvent`.

## 14. UnitOfWork Integration Design
Strict single-aggregate manipulation. `ApplyEvaluationCommand` processes ONE Target Identity. Any fan-out must occur before UoW begins.

## 15. Outbox Integration Design
As always, the Outbox is written to within the `with self.uow:` block immediately after aggregate save.

## 16. Fan-Out Saga Design
`PerformanceFanOutSaga.handle(ThesisEvaluatedEvent)`:
- Extracts Originator, Worker, Strategy IDs from the `ThesisEvaluatedEvent` payload (or associated Context Snapshot).
- Calculates the correct `WindowIdentity` based on `evaluated_at`.
- Publishes three distinct async `ApplyEvaluationCommand` messages to the queue. (No database mutations).

## 17. Metric Registry Design
```python
class MetricRegistry:
    def get_formula(self, version: str) -> Callable[[EvaluationGrade, PredictionMetrics], PredictionMetrics]:
        # Returns exact mathematical function for updating running totals
```
The registry guarantees determinism. Mathematical algorithms are stored explicitly mapped by `MetricVersion`.

## 18. Performance Calculation Design
Calculations rely on incremental rolling math. 
e.g. `new_hit_rate = ((old_hit_rate * old_count) + new_hit) / (old_count + 1)`
Formulas execute inside `MetricRegistry` and output pure VOs back to the Aggregate.

## 19. Database Schema Design
```sql
CREATE TABLE performance_profile_window (
    target_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    window_value TEXT NOT NULL,
    version INT NOT NULL,
    metrics JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    PRIMARY KEY (target_id, target_type, window_value)
);
```

## 20. Sequence Flows
**Evaluation -> Accumulation**
1. System triggers `evaluate_thesis(cmd)`.
2. AppService calls `ThesisEvaluationService.evaluate()`.
3. Outbox `ThesisEvaluatedEvent`.
4. FanOut Saga consumes `ThesisEvaluatedEvent`.
5. FanOut Saga queues 3x `ApplyEvaluationCommand`s.
6. AppService consumes `ApplyEvaluationCommand(Worker_A)`.
7. AppService loads/creates `PerformanceProfileWindow(Worker_A, Q3)`.
8. `profile.apply_evaluation_grade()` -> UoW Commit -> Outbox `PerformanceProfileUpdatedEvent`.

## 21. Validation Rules
- Metrics cannot be negative.
- Brier Score must remain in [0.0, 1.0].
- Cannot apply evaluation to a closed/historical window unless in REPLAY mode.

## 22. Error Handling Design
Standard OCC `ConcurrencyConflictError`.
`MetricVersionNotFoundError` if replaying events from a missing registry algorithm.

## 23. OCC Implementation Design
Native repository SQL enforces `WHERE target_id=%s AND target_type=%s AND window_value=%s AND version=%s`.

## 24. Testing Strategy
- Unit test `MetricRegistry` formulas with strict float precision arrays.
- Unit test FanOut Saga routing logic.
- Integration test UoW database contention on ProfileWindow updates.

## 25. Unit Test Plan
- `test_incremental_brier_calculation_accuracy()`
- `test_fanout_saga_generates_three_commands()`
- `test_evaluation_service_grade_computation()`
- `test_profile_window_version_bump()`

## 26. Integration Test Plan
- `test_postgres_profile_occ_failure()`
- `test_full_evaluate_to_fanout_to_profile_update_flow()`

## 27. Replay Testing Plan
- `test_rebuild_from_thesis_evaluated_events()`: Create 100 historical `ThesisEvaluatedEvent`s, feed them through `RebuildPerformanceProfilesCommand`, and assert the final database JSONB accurately reflects the mathematical sum.

## 28. Migration Plan
Deploy `performance_profile_window` DDL schema. No data backfill required.

## 29. Rollback Plan
Drop schema if DDL fails. Because Performance Engine operates exclusively downstream, the Thesis Engine is unaffected by rollback.

## 30. Risk Assessment
Risk: Floating-point arithmetic drift in rolling calculations.
Mitigation: Brier and hit rate calculations use `decimal` context where precision is critical, or rely on periodic forced rebuilds from the event stream.

## 31. Technical Debt Assessment
The lack of a formal Event Sourcing library forces custom implementation of the `RebuildPerformanceProfilesCommand` replay loop. This debt is acceptable to satisfy the "No New Platform Services" freeze constraint.

## 32. Production Readiness Assessment
Schema is strictly partitioned, OCC enforces concurrency safety, and temporal windows eliminate unbound aggregate growth. Ready for massive throughput.

## 33. Final Implementation Verdict
**READY_FOR_IMPLEMENTATION**
