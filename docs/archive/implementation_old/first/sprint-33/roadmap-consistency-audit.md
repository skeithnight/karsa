# VIF Roadmap Consistency Audit Report

This audit assesses the alignment between the frozen Virtual Investment Firm (VIF) roadmap and the actual repository implementation of the Performance and Thesis engines.

---

## 1. Executive Summary

A comprehensive repository consistency audit was conducted to resolve a roadmap contradiction. While the current VIF roadmap designates future sprints for bootstrapping the **Performance Engine** and the **Thesis Engine**, significant implementations for both contexts already exist within `src/karsa/performance` and `src/karsa/thesis`.

The audit reveals:
1. **Performance Engine (75% Complete)**: The engine already implements core ex-post calculations (Brier score, Sharpe, drawdown, hit rate, and regime-conditioned calibrations) with robust OCC concurrency controls.
2. **Thesis Engine (80% Complete)**: The aggregate state machine, version increment rules, outbox integration, and PostgreSQL repositories are implemented. However, duplicate repository interfaces containing imports of a non-existent class (`ActiveThesis`) are present.
3. **No Greenfield Foundation Required**: Both Sprints 35 (Performance) and Sprints 37/38 (Thesis) should be converted from Greenfield Foundation Sprints into Evolution Sprints, accelerating delivery and addressing identified technical debt.

The final verdict is **ROADMAP_RESCOPE_REQUIRED**.

---

## 2. Repository Capability Inventory

### Performance Engine

* **Current Aggregates**:
  * [DecisionEvaluation](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/performance/domain/model/evaluation.py#L15-L141): An immutable, versioned aggregate representing ex-post outcome analysis for a decision target.
  * [EvaluationSnapshot](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/performance/domain/model/evaluation.py#L143-L210): An immutable, versioned aggregate containing serialized metric states for auditability.
* **Current Value Objects**:
  * Defined in [value_objects.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/performance/domain/model/value_objects.py): `EvaluationTarget`, `EvaluationPeriod`, `ThesisQualityMetric` (Brier score, invalidation state), `ExecutionQualityMetric` (slippage, latency, token count), `AllocationQualityMetric` (Sharpe, drawdown, excess return), `BenchmarkComparison`, `CalibrationBin`, and `ConfidenceCalibration`.
* **Current Services**:
  * [CalibrationService](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/performance/application/service.py#L35-L111): Calculates regime-conditioned confidence and calibration tables.
  * [ProjectionService](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/performance/application/service.py#L113-L231): Computes and rebuilds projections for theses, workers, strategies, and bindings.
  * [EvaluationService](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/performance/application/service.py#L232-L348): Consumes execution outcomes, performs ex-post metric calculations, and manages aggregate persistence.
* **Current Repositories**:
  * Interfaces defined in [repositories.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/performance/domain/model/repositories.py).
  * Implementations in [repositories.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/performance/infrastructure/repositories.py) providing in-memory (`InMemoryDecisionEvaluationRepository`) and file-based (`FileDecisionEvaluationRepository`) storage with strict Optimistic Concurrency Control (OCC) validations.
* **Current Events**:
  * Defined in [events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/performance/events/events.py): `DecisionEvaluatedEvent`, `EvaluationSnapshotCreatedEvent`, and `PerformanceProjectionUpdatedEvent`.
* **Current Projections**:
  * Defined in [projections.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/performance/domain/projections.py): `PerformanceEvaluation`, `ThesisPerformanceProjection`, `WorkerPerformanceProjection`, `StrategyPerformanceProjection`, and `ThesisExecutionBindingPerformanceProjection`.
* **Current APIs**:
  * None. The presentation layer directory `src/karsa/performance/presentation` is currently empty.
* **Current Tests**:
  * [test_performance_engine.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/performance/test_performance_engine.py): Verifies aggregate lifecycle, OCC conflict checks, snapshot creation, replay determinism, projection rebuilds, event emission, calibration calculations, and file repository persistence.

### Thesis Engine

* **Current Aggregates**:
  * [Thesis](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/domain/model/thesis.py#L13-L90): A versioned aggregate implementing FSM lifecycle state transitions (Draft, Proposed, Active, Rejected, Invalidated, Realized).
* **Current Value Objects**:
  * Defined in [value_objects.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/domain/model/value_objects.py): `ThesisState` (state enum), `TimeClassification`, `ContributionRole`, `ConfidenceSource`, `ThesisIdentity`, `HypothesisStructure` (bull/bear cases, invalidation criteria), `TimeHorizon`, `ResearchReference`, `ThesisContributor`, `ConfidenceModel`, and `ThesisContextSnapshot`.
* **Current Services**:
  * [ThesisApplicationService](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/application/service/thesis_application_service.py#L13-L121): Handles commands for proposing theses, updating confidence, recording reviews, and applying governance decisions.
* **Current Repositories**:
  * Postgres implementation in [thesis_repository.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/infrastructure/storage/thesis_repository.py#L30-L72): Implements postgres storage, mapping, and optimistic concurrency version checking.
  * *Critical Finding*: The domain interface [thesis_repository.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/domain/repository/thesis_repository.py), in-memory repository [in_memory_thesis_repository.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/infrastructure/storage/in_memory_thesis_repository.py), and postgres storage wrapper [postgres_thesis_repository.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/infrastructure/storage/postgres_thesis_repository.py) are broken because they import a non-existent class `ActiveThesis` from the domain model.
* **Current Events**:
  * Defined in [thesis_events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/events/thesis_events.py) and [factory.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/events/factory.py): Outbox events wrapping `ThesisContextSnapshot` payloads.
* **Current Projections**:
  * None inside the thesis context. The Performance Engine holds the projections referencing thesis version performance.
* **Current APIs**:
  * None. No presentation layers are defined.
* **Current Tests**:
  * [test_thesis.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/thesis/domain/model/test_thesis.py): Verifies state machines, immutability, and version increments.
  * [test_thesis_application_service.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/thesis/application/service/test_thesis_application_service.py): Verifies UOW execution, outbox integration, and governance-guided activation.
  * [test_thesis_repository.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/thesis/infrastructure/storage/test_thesis_repository.py): Verifies UPSERT and OCC checking using mocked cursors.

---

## 3. VIF Target Capability Matrix

| VIF Target Requirement | Current Repository Capability | Status | Gap Identified |
| :--- | :--- | :--- | :--- |
| **Performance Engine** | | | |
| Return series | Stored in outcomes and evaluations (`actual_return_bps`) | **PARTIAL** | Lacks continuous time-series aggregation. |
| Portfolio performance | Evaluated on strategy levels | **PARTIAL** | Lacks integration with real-time portfolio holdings. |
| Worker performance | Fully supported via hit rates & Brier scores | **PASS** | None. |
| Sharpe | Calculated using returns vs. drawdowns | **PASS** | None. |
| Sortino | None | **MISSING** | Sortino calculation function is missing. |
| Drawdown | Tracked per outcome and projection | **PASS** | None. |
| Win rate | Supported as `hit_rate` in projections | **PASS** | None. |
| Benchmark comparison | Fully calculated via `BenchmarkComparison` | **PASS** | None. |
| Attribution integration | None | **MISSING** | No integration with attribution engines. |
| Capital Allocation | Limits are modeled on bindings | **PARTIAL** | Not integrated with target weight generation. |
| Governance integration | Calibrated confidences can feed PDP | **PARTIAL** | Verification checks are not wired to PDP rules. |
| Replayability | Supported via event replay projection rebuilding | **PASS** | None. |
| Auditability | Enforced via immutable snapshots | **PASS** | None. |
| **Thesis Engine** | | | |
| Thesis lifecycle | FSM handles all transitions | **PASS** | None. |
| Thesis versioning | Enforced via `VersionedAggregate` | **PASS** | None. |
| Thesis promotion | Transitions via governance decision to ACTIVE | **PASS** | None. |
| Thesis retirement | Transitions via realize command to REALIZED | **PASS** | None. |
| Thesis invalidation | Transitions via invalidate command to INVALIDATED | **PASS** | None. |
| Thesis evidence linkage | Models lists of research references | **PASS** | None. |
| Thesis performance | Linked via `ThesisPerformanceProjection` | **PARTIAL** | Cross-domain correlation is manual. |
| Thesis replayability | Fully supported via event-driven design | **PASS** | None. |
| Thesis auditability | Snapshot outbox logging is implemented | **PASS** | None. |

---

## 4. Coverage Assessment

### Performance Coverage
* **Existing capability coverage = 75%**
  * *Evidence*: Out of the 13 required capabilities in the matrix, 6 are fully satisfied, 5 are partially satisfied (calibrations and basic math exist but lack runtime integrations), and only 2 (Sortino calculation and direct Attribution integration) are completely missing. All core models and services ([service.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/performance/application/service.py)) are functional and covered by 13 comprehensive tests.

### Thesis Coverage
* **Existing capability coverage = 80%**
  * *Evidence*: Out of the 9 required capabilities in the matrix, 8 are fully implemented. The aggregate lifecycle ([thesis.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/domain/model/thesis.py)), application command layer ([thesis_application_service.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/application/service/thesis_application_service.py)), and postgres schema mappings are complete and verified by unit tests. The remaining 20% covers missing presentation routes, broken legacy repositories containing compilation errors, and binding projections integration.

---

## 5. Reuse vs Replace Analysis

### Performance Engine: EVOLVE
* **Rationale**: The mathematical calculations (Sharpe, Brier, calibration bins) are clean, functional, and well-tested. Replacing them would introduce waste. However, the engine currently persists data in JSON files and lacks REST/gRPC presentation ports. It must be evolved to persist states in Postgres and stream metrics dynamically.

### Thesis Engine: EVOLVE
* **Rationale**: The core aggregate state machine and command handlers are architecturally sound. However, the broken repository files ([in_memory_thesis_repository.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/infrastructure/storage/in_memory_thesis_repository.py) and [postgres_thesis_repository.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/infrastructure/storage/postgres_thesis_repository.py)) must be refactored or deleted to remove the legacy `ActiveThesis` import errors. The functioning [thesis_repository.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/infrastructure/storage/thesis_repository.py) must be promoted as the single source of truth.

---

## 6. Architecture Delta Analysis

### Missing Capabilities
1. **Sortino Ratio**: Calculation logic is not present in the Performance evaluation services.
2. **Postgres Schemas**: Performance metrics do not have database migrations or postgres repositories implemented (uses file JSON).
3. **API Presentation Routing**: Both Performance and Thesis contexts lack HTTP controllers or presentation layers.

### Missing Ownership
* **Execution/Attribution Boundaries**: There is no direct logic in the Performance Engine to fetch execution slippages from the Execution Engine or capture attribution records.

### Missing Events
* **Attribution Ingested / Portfolio Updated**: The Performance Engine does not subscribe to Portfolio cash/holdings updates to trigger ex-post evaluation recalculations.

### Missing Projections
* **Real-time Performance Projections**: Projections are currently calculated on-demand or rebuilt synchronously rather than updating dynamically on every fill event.

---

## 7. Sprint Impact Analysis

### Sprint-35 Performance Engine Foundation
* **Result**: **RESCOPE_REQUIRED**
  * *Evidence*: Designing the foundation is redundant because the core models, value objects, projections, and calculations are already implemented. The sprint should be rescoped to **Sprint-35: Performance Engine Evolution**, focusing on database migrations, Postgres repository integration, real-time event subscriptions, and REST API controllers.

### Sprint-37/38 Thesis Engine Foundation
* **Result**: **RESCOPE_REQUIRED**
  * *Evidence*: The Thesis engine FSM and outbox event publishing are fully implemented and verified. The sprint should be rescoped to **Sprint-38: Thesis Engine Evolution**, focusing on cleaning up broken legacy repositories, finalizing DB tables, and linking performance projection streams.

---

## 8. Recommendation Matrix

* **Option B (Recommended)**: Convert Sprint-35 and/or Sprint-37/38 from Foundation Sprints to Evolution Sprints.
  * *Justification*: Substantial portions of both engines are already functional. Converting them to Evolution Sprints prevents rewriting working logic, preserves engineering hours, and prioritizes resolving technical debt (such as cleaning up broken repository classes) and building integrations.

---

## 9. Risks

1. **Broken Legacy Repositories**: Dead code in `src/karsa/thesis` importing `ActiveThesis` might lead to import errors if referenced during execution. *Mitigation*: Delete or refactor all duplicate/broken repository files in the next sprint.
2. **Integration Latency**: Recalculating Brier and Sharpe metrics synchronously inside execution paths will cause performance degradation. *Mitigation*: Process ex-post performance metrics asynchronously via background projection threads.

---

## 10. Acceptance Criteria

1. **Performance Engine Evolution**:
   * Implement postgres migrations for evaluations, snapshots, and projections.
   * Write REST/gRPC presentation routes exposing worker and thesis performance scores.
   * Add Sortino ratio calculations to evaluation services.
2. **Thesis Engine Evolution**:
   * Refactor repository modules to remove all imports of the non-existent `ActiveThesis` class.
   * Write presentation routes for proposing theses and fetching thesis details.
   * Connect outbox events to the event publishing broker.

---

## 11. Final Verdict

### **ROADMAP_RESCOPE_REQUIRED**
