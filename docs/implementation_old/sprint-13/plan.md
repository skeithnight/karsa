# Sprint-13 Performance Engine Foundation Architecture Design

## 1. Executive Summary
The Sprint-13 Performance Engine Foundation establishes the canonical framework for evaluating the historical accuracy and effectiveness of investment hypotheses within the Karsa Virtual Investment Firm. It introduces the `PerformanceProfile` as the authoritative aggregate for accumulating metrics on Originators, Workers, and Strategies. By decoupling scoring logic from the Thesis Engine and isolating it from future Attribution and Capital Allocation engines, this architecture ensures high cohesion. The system leverages the existing asynchronous `PlatformEventEnvelope` infrastructure to consume thesis outcomes (`ThesisRealizedEvent`, `ThesisInvalidatedEvent`) and incrementally recalculate calibration and hit rates without mutating upstream aggregates.

## 2. Ownership Boundary Matrix
| Concept | Bounded Context | Description |
|---------|-----------------|-------------|
| `PerformanceProfile` | WP-13 Performance Engine | Aggregate root maintaining the rolling track record of an entity. |
| `ThesisScoreRecord` | WP-13 Performance Engine | VO representing the evaluated outcome of a single thesis. |
| `ScoringStrategy` | WP-13 Performance Engine | Domain service defining the math to evaluate a thesis. |
| `Thesis` | WP-12 Thesis Engine | Upstream aggregate that dictates intent. |
| `AllocationBudget` | WP-16 Capital Allocation | Downstream consumer of performance profiles. |

## 3. Architecture Overview
The Performance Engine operates as a downstream reactive consumer. It subscribes to `ThesisRealizedEvent` (success) and `ThesisInvalidatedEvent` (failure) from the Thesis Engine. Upon receiving a terminal thesis state, it calculates a discrete `ThesisScoreRecord` using the thesis's original `ConfidenceModel`. It then retrieves or creates the `PerformanceProfile` for the associated `Originator` (and explicitly the worker and strategy), applies the new score incrementally, and persists the updated profile using the standard `UnitOfWork` and `Outbox` OCC pattern. 

## 4. Domain Model
- **`PerformanceProfile` (Aggregate Root)**: Tracks aggregate statistics for a specific target.
- **`TargetIdentity` (Value Object)**: The entity being tracked (e.g., TargetType.ORIGINATOR, TargetType.WORKER, TargetType.STRATEGY).
- **`PerformanceMetrics` (Value Object)**: Contains `hit_rate`, `brier_score` (calibration), `total_evaluated`, `success_count`, `failure_count`.
- **`ThesisScoreRecord` (Value Object)**: Represents the result of a single evaluated thesis: `thesis_id`, `outcome` (SUCCESS/FAILURE), `original_confidence`, `score_impact`.

## 5. Aggregate Design
The `PerformanceProfile` aggregate maintains strict transaction boundaries. It owns the `PerformanceMetrics` object. When `apply_thesis_score(score: ThesisScoreRecord)` is called, the aggregate incrementally updates its metrics (e.g., recalculating the running Brier Score) and increments its `aggregate_version`. It explicitly limits its scope to statistical accumulation, deferring PnL calculations to the Attribution Engine.

## 6. Value Objects
- **`TargetIdentity`**: `target_id: str`, `target_type: str`
- **`PerformanceMetrics`**: 
  - `total_evaluated: int`
  - `success_count: int`
  - `failure_count: int`
  - `hit_rate: float`
  - `brier_score: float`
- **`ThesisScoreRecord`**: `thesis_id: str`, `resolution: str`, `confidence_at_resolution: float`, `brier_penalty: float`.

## 7. Event Contracts
- **Consumed**:
  - `ThesisRealizedEvent` -> Interpreted as SUCCESS.
  - `ThesisInvalidatedEvent` -> Interpreted as FAILURE.
- **Produced**:
  - `PerformanceProfileUpdatedEvent` (Payload includes `TargetIdentity` and new `PerformanceMetrics`).
  - `ThesisScoredEvent` (Payload includes the discrete `ThesisScoreRecord`).

## 8. Application Services
- `ScoreThesisApplicationService`:
  - `handle_thesis_realized(event)`
  - `handle_thesis_invalidated(event)`
  - `recalculate_profile(cmd)` (For forced rebuilds).

## 9. Repositories
- `PerformanceProfileRepository`: Standard `save()` and `get_by_identity()` interface protecting the Aggregate.

## 10. Persistence Design
Leveraging PostgreSQL JSONB (similar to Sprint-12). 
`CREATE TABLE performance_profile ( target_id TEXT, target_type TEXT, version INT, metrics JSONB, PRIMARY KEY (target_id, target_type) );`

## 11. Integration Design
Integration is strictly asynchronous. The Performance Engine's event listener polls the Institutional Memory or Kafka topic for terminal Thesis events. It publishes `PerformanceProfileUpdatedEvent` which will be critical for Sprint-16 (Capital Allocation Engine) to adjust risk budgets dynamically.

## 12. Sequence Diagrams
1. Thesis Engine emits `ThesisRealizedEvent` (Outbox -> Kafka).
2. Performance Engine consumes event.
3. `ScoreThesisApplicationService.handle_thesis_realized()`:
   - Calculates `ThesisScoreRecord` (e.g., Brier score penalty based on confidence).
   - Loads `PerformanceProfile` for the Originator, Worker, and Strategy.
   - For each profile: `profile.apply_score(record)`.
   - Saves profiles via `UnitOfWork`.
   - Stages `PerformanceProfileUpdatedEvent` to Outbox.
4. Transaction commits.

## 13. State Diagrams
`PerformanceProfile` has no explicit lifecycle states (like DRAFT/ACTIVE). It is instantiated on first use and continuously evolves via mathematical accumulation.

## 14. Failure Handling
Uses OCC to prevent race conditions if multiple theses for the same originator resolve simultaneously. `ConcurrencyConflictError` triggers a standard retry-loop at the consumer boundary.

## 15. OCC Strategy
`UPDATE performance_profile SET metrics = ?, version = ? WHERE target_id = ? AND target_type = ? AND version = ?`. `rowcount == 0` raises `ConcurrencyConflictError`.

## 16. Scalability Analysis
Calculating running averages (Hit Rate, Brier Score) is O(1) space complexity. The aggregate does not store the array of historical `ThesisScoreRecord`s. It only stores the scalar running totals. This prevents the aggregate from bloating into megabytes over years of trading.

## 17. Security Analysis
Governance separation ensures that neither a Worker nor an Originator can alter their own `PerformanceProfile`. The engine is a closed loop, purely reactive to authorized `PlatformEventEnvelope` transitions.

## 18. Migration Strategy
Net-new bounded context. Schema initialization via DDL. No legacy data to migrate.

## 19. Risks
**Risk**: Incremental floating-point calculations (e.g., rolling averages) may drift over millions of events due to precision loss.
**Mitigation**: The design allows full profile wiping and re-computation from the immutable Institutional Memory event stream if drift is detected.

## 20. ADR Decisions
- **ADR-13.1**: `PerformanceProfile` is scoped by `TargetIdentity` rather than combining Originator, Worker, and Strategy into one massive matrix. *Rationale*: Allows independent querying and prevents severe lock contention. A single thesis resolution updates three separate, isolated `PerformanceProfile` aggregates (one for Originator, one for Worker, one for Strategy).
- **ADR-13.2**: `ThesisScoreRecord` is NOT stored inside `PerformanceProfile`. *Rationale*: Aggregate size bounds must be strictly enforced. History is reconstructed from the event stream.

## 21. Architecture Challenges
**Challenge**: How to handle a `Thesis` that was resolved, but later the resolution is reversed due to a data error?
**Resolution**: The Performance Engine must handle compensatory events. If a `ThesisInvalidatedEvent` is reverted, the engine recalculates the score mathematically by inverting the previous `ThesisScoreRecord` parameters against the rolling metrics.

## 22. Architecture Delta Analysis
Compared to the baseline Sprint-12 architecture, this introduces purely analytical tracking aggregates. It establishes the mathematical feedback loop required for AI-calibration without polluting the intent-based `Thesis` aggregate.

## 23. Acceptance Criteria
- Aggregate handles Originator, Worker, and Strategy identities independently.
- Computes Hit Rate and Brier Score accurately.
- Consumes Terminal Thesis events exclusively.
- Strict OCC and single aggregate transactions utilized.
- No PnL or Capital calculations exist in the domain.

## 24. Final Verdict
**READY_FOR_FREEZE**

---

## Design Decisions & Required Answers

**1. What is the Aggregate Root of Performance?**
The Aggregate Root is `PerformanceProfile`. It tracks the historical statistical metrics for a single entity (identified by `TargetIdentity`), ensuring transactional boundaries are narrow and focused.

**2. Is performance calculated incrementally or recomputed?**
Calculated *incrementally*. Each terminal event updates the running totals in `PerformanceProfile.metrics`. Total recomputation is reserved only for system disaster recovery or metric version changes, powered by Institutional Memory.

**3. How are thesis outcomes measured?**
Outcomes are binary in this sprint: `ThesisRealizedEvent` = SUCCESS (Outcome=1.0), `ThesisInvalidatedEvent` = FAILURE (Outcome=0.0). Continuous scoring (e.g., partial profit) is deferred to the Attribution Engine.

**4. How are originators ranked?**
**5. How are workers ranked?**
**6. How are strategies ranked?**
They are ranked by querying the read-models of the `PerformanceProfile` aggregates. Because the engine generates a separate `PerformanceProfile` for each `TargetIdentity` (Originator, Worker, Strategy), the Capital Allocation engine can subsequently rank them by sorting their `brier_score` or `hit_rate`.

**7. What performance metrics are first-class?**
- `hit_rate` (Successes / Total)
- `brier_score` (Mean squared difference between predicted confidence and actual outcome, enforcing strict calibration accuracy).

**8. How is performance history stored?**
History is strictly maintained in the immutable event log (`ThesisScoredEvent`, `PerformanceProfileUpdatedEvent`). The aggregate stores only the present snapshot.

**9. How does performance integrate with Thesis Engine?**
Via asynchronous consumption of `ThesisRealizedEvent` and `ThesisInvalidatedEvent`. There is zero synchronous coupling.

**10. How does performance integrate with future Attribution Engine?**
The Attribution Engine will listen to `ThesisScoredEvent` and map the PnL of specific trades to that thesis, enriching the performance context with financial magnitude.

**11. How does performance integrate with future Capital Allocation Engine?**
The Capital Allocation Engine will listen to `PerformanceProfileUpdatedEvent` to dynamically expand or constrict the risk budget of a Worker based on their shifting calibration accuracy.

**12. How is replayability guaranteed?**
Because the math is deterministic and relies strictly on data inside the `PlatformEventEnvelope`, wiping the `performance_profile` table and replaying the event stream from time=0 will perfectly reconstruct the state.

**13. How is auditability guaranteed?**
Every mathematical mutation inside the `PerformanceProfile` triggers a `PerformanceProfileUpdatedEvent` that includes a `causation_id` pointing back to the specific `Thesis` event that caused the shift.

**14. How are recalculations handled?**
If a new metric is introduced, a batch job emits a `RebuildPerformanceProfileCommand`, which wipes the table and replays the stream using the updated domain logic.

**15. How are metric version changes handled?**
The `PerformanceMetrics` value object is versioned. When a new mathematical formula is adopted (e.g., v2 Brier Score calculation), the schema_version of the resulting events increments, signaling downstream consumers of the logic shift.