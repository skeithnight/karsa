# Sprint-13 Performance Engine Foundation - Architecture Revision v1

## 1. Executive Summary
The Sprint-13 Performance Engine Foundation establishes the canonical mathematical evaluation and tracking layer for the Karsa Virtual Investment Firm. This revision fundamentally resolves early architecture flaws by introducing a strict Event Fan-Out pattern to preserve Single Aggregate UnitOfWork constraints, formalizing the `ThesisEvaluation` as an explicit aggregate to handle nuanced success/failure grades, and bifurcating Prediction Quality from Investment Quality. It explicitly scopes the Performance Engine as the authoritative owner of scoring formulas while maintaining absolute deterministic replayability via Institutional Memory.

## 2. Ownership Boundary Matrix
| Concept | Bounded Context | Description |
|---------|-----------------|-------------|
| `PerformanceProfile` | WP-13 Performance Engine | Tracks running metrics for a single identity (Originator/Worker/Strategy). |
| `ThesisEvaluation` | WP-13 Performance Engine | Evaluates a single thesis outcome vs intent. |
| `PredictionMetrics` | WP-13 Performance Engine | VO defining Brier scores, hit rates, and timing. |
| `InvestmentMetrics` | WP-13 Performance Engine | VO defining ROI, Capital Efficiency (Placeholders for Sprint-14). |
| `ScoringFormula` | WP-13 Performance Engine | Versioned domain service defining mathematical metrics. |

## 3. Architecture Overview
The architecture is divided into two phases: **Evaluation** and **Accumulation**.
1. **Evaluation**: When a Thesis is realized or invalidated, an asynchronous saga initiates a `ThesisEvaluation` aggregate. This aggregate compares expected intent vs actual outcome (simulated/manual for now), producing a nuanced `ThesisEvaluatedEvent`.
2. **Accumulation**: The `ThesisEvaluatedEvent` triggers an Event Fan-Out. Separate commands are dispatched to update the Originator, Worker, and Strategy `PerformanceProfile` aggregates individually, preserving strict OCC and single-aggregate bounds.

## 4. Domain Model
- **`ThesisEvaluation` (Aggregate Root)**: Represents the multi-dimensional scoring of a single thesis.
- **`PerformanceProfile` (Aggregate Root)**: Represents the rolling historical track record of a single Target Identity.
- **`EvaluationGrade` (Value Object)**: Contains `prediction_score` (0.0 to 1.0), `investment_score` (continuous PnL representation), `timing_score`.
- **`MetricDefinition` (Value Object)**: Tracks the `schema_version` of the formulas used.

## 5. Aggregate Design
- **`ThesisEvaluation`**: Created per thesis resolution. State: `PENDING_DATA` -> `EVALUATED`. Owns the complex logic of scoring magnitude (e.g., Expected +40%, Actual +5% -> `prediction_score` = 0.125).
- **`PerformanceProfile`**: Maintains rolling `PredictionMetrics` and `InvestmentMetrics`. Only accepts `ApplyEvaluationCommand`. Mutates state incrementally and bumps `aggregate_version`.

## 6. Value Objects
- **`TargetIdentity`**: `target_id: str`, `target_type: str` (ORIGINATOR, WORKER, STRATEGY).
- **`PredictionMetrics`**: `hit_rate: float`, `brier_score: float`, `evaluation_count: int`.
- **`InvestmentMetrics`**: `average_roi: float`, `capital_efficiency_score: float` (populated post-Sprint-14).
- **`EvaluationGrade`**: `prediction_score: float`, `investment_score: float`, `timing_score: float`.
- **`MetricVersion`**: `version: str`, `algorithm_hash: str`.

## 7. Event Contracts
- `ThesisRealizedEvent` / `ThesisInvalidatedEvent` (Consumed)
- `ThesisEvaluationStartedEvent` (Produced)
- `ThesisEvaluatedEvent` (Produced - Contains full `EvaluationGrade`)
- `PerformanceProfileUpdatedEvent` (Produced per TargetIdentity)

## 8. Application Services
- **`ThesisEvaluationService`**: Evaluates thesis. Emits `ThesisEvaluatedEvent`.
- **`PerformanceProfileService`**: Receives `ApplyEvaluationCommand` specific to ONE target. Loads profile, increments stats, saves, emits `PerformanceProfileUpdatedEvent`.
- **`PerformanceFanOutSaga`**: Subscribes to `ThesisEvaluatedEvent` and generates exactly N discrete `ApplyEvaluationCommand`s for Originator, Worker, and Strategy.

## 9. Repositories
- `ThesisEvaluationRepository`: Stores evaluation artifacts.
- `PerformanceProfileRepository`: Stores profile metrics with OCC.

## 10. Persistence Design
- `thesis_evaluation` table: `evaluation_id`, `thesis_id`, `grade_jsonb`, `version`.
- `performance_profile` table: `target_id`, `target_type`, `metrics_jsonb`, `version`.
Both heavily rely on JSONB for complex Value Object structures to prevent joins.

## 11. Integration Design
All communication is Outbox-driven. The `PerformanceFanOutSaga` guarantees that a single thesis resolution safely propagates to multiple profiles without UoW spanning.

## 12. Sequence Diagrams
1. Thesis Engine -> `ThesisRealizedEvent`.
2. Evaluation Engine -> Creates `ThesisEvaluation` -> Saves -> Outbox `ThesisEvaluatedEvent`.
3. FanOut Saga consumes `ThesisEvaluatedEvent`.
4. FanOut Saga publishes:
   - `ApplyEvaluation(target=Originator)`
   - `ApplyEvaluation(target=Strategy)`
   - `ApplyEvaluation(target=Worker)`
5. Profile Service consumes `ApplyEvaluation(Originator)`. UoW -> Load Profile -> Apply Math -> Save -> Outbox `PerformanceProfileUpdatedEvent` -> Commit.

## 13. State Diagrams
- **`ThesisEvaluation`**: `EVALUATING` -> `EVALUATED` | `FAILED_MISSING_DATA`.
- **`PerformanceProfile`**: No states, pure continuous mathematical accumulation.

## 14. Failure Handling
If `ApplyEvaluationCommand` fails due to OCC (`ConcurrencyConflictError`), the Kafka/RabbitMQ consumer retries the message. Because profiles are isolated, Originator updates do not lock Strategy updates.

## 15. OCC Strategy
Standard `VersionedAggregate` strategy applied to both `ThesisEvaluation` and `PerformanceProfile`. `UPDATE ... WHERE version = X`.

## 16. Scalability Analysis
Fan-Out prevents single-row hotspots. Originators executing thousands of theses concurrently will experience OCC contention on their `PerformanceProfile`. Jittered retries at the queue level gracefully absorb this contention.

## 17. Security Analysis
Profiles are mathematically deterministic and cannot be updated directly via API. They are exclusively mutated via the internal event bus.

## 18. Migration Strategy
Net-new context. DDL deployment only.

## 19. Risks
- Delay in future Attribution Engine data means `InvestmentMetrics` will remain `null` or placeholder for Sprint-13.
- Mitigation: Architecture supports partial evaluation grades.

## 20. ADR Decisions
- **ADR-13.3**: Split Evaluation from Profile Accumulation. *Rationale*: Resolves the Single Aggregate UoW violation by utilizing an Event Fan-Out pattern.
- **ADR-13.4**: Separate Prediction and Investment Metrics. *Rationale*: Brier score (accuracy) is distinct from ROI (magnitude). A worker can be highly accurate on low-value trades and highly inaccurate on high-value trades. Both must be measured independently.

## 21. Architecture Challenges
**Challenge**: Deterministic replayability when mathematical formulas change.
**Resolution**: Institutional Memory stores `ThesisEvaluatedEvent` containing the raw `EvaluationGrade`. Replaying events rebuilds the exact profiles. If a *new* formula is desired, the `ThesisEvaluation` aggregate itself must be replayed to emit new `ThesisEvaluatedEvent`s under a new `schema_version`.

## 22. Architecture Delta Analysis
This revision introduces the `ThesisEvaluation` aggregate and Event Fan-Out saga, fixing the transactional boundaries and introducing a nuanced, multi-dimensional scoring model in place of the rudimentary binary pass/fail system.

## 23. Acceptance Criteria
- Single Aggregate per UoW constraint rigorously maintained.
- `ThesisEvaluation` aggregate handles magnitude-based scoring.
- Prediction vs Investment metrics logically segregated.
- Rebuild architecture fully defined without data loss risks.

## 24. Final Verdict
**ARCHITECTURE_READY_FOR_FREEZE**

---

## 25. Review Findings Resolution Matrix

### Finding #1: Single Aggregate Violation
**Resolution**: Implemented Event Fan-Out via `PerformanceFanOutSaga`. One `ThesisEvaluatedEvent` explicitly generates distinct, atomic commands for each target identity, ensuring no single UoW locks multiple profiles.

### Finding #2: Missing Canonical Thesis Evaluation Model
**Resolution**: Introduced `ThesisEvaluation` aggregate. Replaces binary scoring with `EvaluationGrade` capturing partial successes, magnitude errors, and timing deviations.

### Finding #3: Prediction Quality vs Investment Quality
**Resolution**: Split `PerformanceMetrics` into `PredictionMetrics` (hit rate, Brier score) and `InvestmentMetrics` (capital efficiency, ROI placeholders). Allows Capital Allocation Engine to budget differently based on risk profiles.

### Finding #4: Metric Definition Ownership
**Resolution**: The Performance Engine natively owns `ScoringFormula` domain services. All emitted evaluation events stamp the exact `MetricVersion` used, locking the mathematical definition in history.

### Finding #5: Replayability Gap
**Resolution**: `PerformanceProfile` rebuilds strictly by re-applying historical `ThesisEvaluatedEvent`s. The events contain the discrete score impacts, ensuring that rolling averages can be deterministically reconstructed from Time=0.

---

## 26. Rejected Alternatives
- **Synchronous Fan-Out in UoW**: Rejected due to Sprint-11.5 OCC deadlock constraints.
- **Combined Target Profiles**: Rejected. Storing Originator, Worker, and Strategy in one matrix aggregate would cause unmanageable aggregate bloat.
- **Binary Outcome Scoring**: Rejected. Fails to capture edge cases (e.g., expected +20%, actual +200%).

## 27. Tradeoff Analysis
- **Tradeoff**: Event Fan-Out introduces eventual consistency. A user querying performance immediately after thesis realization may see stale metrics.
- **Justification**: This is acceptable. Performance is a slow-moving analytical calculation. Uptime and lock-contention mitigation outweigh real-time consistency.

## 28. Future Compatibility Assessment
The separation of `PredictionMetrics` and `InvestmentMetrics` perfectly sets up the Sprint-14 Attribution Engine to backfill the `InvestmentMetrics` via compensatory events without rewriting the evaluation model.

## 29. Replayability Assessment
Flawless. Rebuilding requires only draining the Kafka topics containing `ThesisEvaluatedEvent` and re-applying the basic arithmetic (averages, sums) to fresh `PerformanceProfile` aggregates.

## 30. Freeze Readiness Assessment
All findings resolved. Transaction boundaries conform to strict DDD principles. The mathematical evaluation layer is securely decoupled from the intent layer. **READY FOR FINAL FREEZE**.
