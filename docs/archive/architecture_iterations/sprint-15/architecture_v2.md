# Sprint-15 Performance Engine Foundation - Architecture Revision v2

## 1. Executive Summary
The Sprint-15 Performance Engine Foundation Revision v2 fundamentally pivots the system from a Worker-centric analytics dashboard into a rigorous, Decision-centric intelligence graph. By formalizing the `DecisionPerformanceRecord` as the canonical unit of performance, the engine achieves profound post-mortem and review capabilities while enabling real-time drawdown awareness for the Capital Allocation Engine. The architecture explicitly renounces a secondary event log, designating Institutional Memory as the exclusive Source of Truth. Through a comprehensive hierarchical projection strategy, it guarantees mathematically pure, high-fidelity metrics spanning multi-dimensional Calibration, Regime effectiveness, and real-time Capital Allocation integration.

## 2. Ownership Boundary Matrix
- **Attribution Engine**: Owns the mathematical fractional split of absolute financial value resulting from an outcome.
- **Performance Engine**: Owns the longitudinal, probabilistic evaluation of decisions, workers, strategies, regimes, and calibration models.
- **Review Engine**: Owns post-mortem analysis (e.g., "Why did this decision fail? Was it execution or thesis flaw?").
- **Capital Allocation Engine**: Owns the virtual/real portfolio sizing derived from performance metrics and ranking scores.
- **Governance Engine**: Owns human-in-the-loop approvals, restatements, and intervention logic.

## 3. Architecture Overview
The Performance Engine is an asynchronous, event-driven CQRS Projection Engine. It monitors Institutional Memory for `AttributionCalculatedEvent`, `ThesisResolvedEvent`, and `RegimeChangedEvent`s. Upon ingestion, it synthesizes these into a canonical `DecisionPerformanceRecord` representing the absolute ground-truth evaluation of a single decision. From this record, real-time projections map the impact to Worker, Strategy, Regime, and Calibration profiles.

## 4. Domain Model
- **`DecisionPerformanceRecord`**: The foundational, canonical, event-sourced entity linking an outcome back to a decision.
- **`PerformanceProjector`**: Stateless domain service orchestrating the cascade from Decision -> Hierarchical Profiles.
- **`CalibrationEvaluator`**: Dedicated service evaluating hit-rates and Brier scores against multi-dimensional decision metadata.

## 5. Aggregate Design
**Zero Aggregates**
The Performance bounded context holds no standard domain Aggregates. The primary unit of modeling is the immutable `DecisionPerformanceRecord`, which functions purely as a Rebuildable Read Model derived directly from Institutional Memory. All subsequent profiles (Worker, Strategy) are nested projections.

## 6. Value Objects
- **`DecisionPerformanceIdentity`**: `decision_id`, `outcome_sequence_id`.
- **`CalibrationMetrics`**: `brier_score`, `hit_rate`, `stated_confidence`, `outcome_binary`.
- **`RiskAdjustedMetrics`**: `gross_pnl`, `max_drawdown`, `sharpe_proxy`.

## 7. Event Contracts
- **`DecisionPerformanceEvaluatedEvent`**: Fired in real-time when a decision's performance impact is formalized.
- **`WorkerPerformanceUpdatedEvent`**: Real-time signal containing delta metrics for Capital Allocation triggers.

## 8. Application Services
- **`RealTimePerformanceProcessor`**: Consumes raw Institutional Memory events and constructs the `DecisionPerformanceRecord`.
- **`HierarchicalProjectionOrchestrator`**: Triggers cascading updates to secondary profiles (Worker, Strategy, Regime, Calibration).

## 9. Repositories
- **`DecisionPerformanceStore`**: Fast-read Key-Value/Document store for the canonical records.
- **`HierarchicalProfileStore`**: Projection repository for materialized views (Worker, Regime, etc).

## 10. Persistence Design
- **`decision_performance_record`**: Core table mapping decision identity to its financial and calibration metadata.
- **`projection_*` tables**: Multi-dimensional rolling views. All persistence acts exclusively as a rebuildable cache.

## 11. Integration Design
- Listens to: `AttributionCalculatedEvent`, `ThesisResolvedEvent`, `RegimeChangedEvent` (from Institutional Memory).
- Emits: Real-time downstream update events tailored for Capital Allocation and Review Engines.

## 12. Sequence Diagrams
1. `AttributionCalculatedEvent` emitted.
2. `RealTimePerformanceProcessor` queries Institutional Memory for prior `ThesisResolvedEvent` and `DecisionContext`.
3. `DecisionPerformanceRecord` constructed and persisted.
4. Projection cascade updates `WorkerPerformanceProfile`, `RegimePerformanceProfile`, etc.
5. Emits real-time `WorkerPerformanceUpdatedEvent` for instantaneous capital sizing.

## 13. State Diagrams
Projections lack lifecycles. They are pure mathematical reductions of the `DecisionPerformanceRecord` stream.

## 14. Failure Handling
If projection calculations drift or fail, the entire subsystem is wiped and rehydrated linearly from Institutional Memory without data loss.

## 15. OCC Strategy
Because performance operations are exclusively idempotent projections bound to chronological `outcome_sequence_id`s, traditional locking is bypassed via Upsert (`ON CONFLICT DO UPDATE`) semantics.

## 16. Scalability Analysis
Decoupling the Source of Truth to Institutional Memory completely isolates Performance scaling from transaction ingestion. Streaming updates ensure O(1) processing times per event.

## 17. Security Analysis
Immutable events verify all historical PNL. No human can edit a `WorkerPerformanceProfile` directly; they must push governance-approved restatements upstream to Attribution.

## 18. Migration Strategy
Initialize `decision_performance_record` schema. Wipe any V1 ledger logic.

## 19. Risks
Rebuilding projections over millions of outcomes can be temporally expensive. Addressed via regular indexed snapshots inside the Projection Store.

## 20. ADR Decisions
- **ADR-15.03**: Decision-Centricity. The atomic unit of performance evaluation is the Decision, not the Worker. 
- **ADR-15.04**: Pure CQRS Cache. The Performance Engine holds absolutely zero canonical data. Institutional Memory is the sole Source of Truth.
- **ADR-15.05**: Real-Time Invalidation. Projections are updated and events published in near real-time (Option B) to support high-frequency drawdown defense mechanisms in the Capital Engine.

## 21. Architecture Challenges
*(Closed)*

## 22. Architecture Delta Analysis
Shifted entirely from Worker-centric ledgers (v1) to Decision-centric intelligence graphs (v2). Daily batches abandoned for real-time projection cascades.

## 23. Acceptance Criteria
1. Rebuilding the database from Institutional Memory yields byte-for-byte identical projection states.
2. `RegimePerformanceProfile` successfully clusters decisions made in distinct temporal regimes.
3. `CalibrationProfile` reliably outputs Brier scores evaluating thesis confidence against binary outcomes.

## 24. Final Verdict
**READY_FOR_ARCHITECTURE_REVIEW**

## 25. Performance Metric Model
- **Cumulative Financial Impact**: `gross_pnl`, `net_pnl`.
- **Probabilistic Accuracy**: `hit_rate` (Positive vs Negative PNL).
- **Risk Velocity**: `max_drawdown`, `volatility_proxy` (Standard Deviation of decision returns).

## 26. Performance Window Model
Windows (30D, 90D, 180D, LIFETIME) are purely real-time rolling calculations materialized inside the projections. The daily cron is eliminated in favor of continuous temporal sliding window updates triggered by new events.

## 27. Ranking Model
Ranking operates via specialized asynchronous queries running against the materialized Read Models. As decisions stream in, rank indexes are re-sorted natively inside the database engine.

## 28. Regime Compatibility Model
**`RegimePerformanceProfile`**: First-class projection. A worker's decisions are sliced by `regime_id`. The Capital Engine can directly query a Worker's performance under `HIGH_VOLATILITY` vs `RANGE_BOUND` environments to size limits accordingly.

## 29. Confidence Calibration Model
**`CalibrationProfile`**: A multi-dimensional matrix. It slices Brier Scores (Confidence vs Reality) across Worker, Strategy, Market Cap, Sector, and Horizon.
*Example Output*: Worker A has an excellent 0.05 Brier score on Tech/Large-Cap, but a terrible 0.40 Brier score on Crypto/Small-Cap. This granular matrix allows the Review Engine to definitively highlight bias traps.

## 30. Capital Allocation Readiness Analysis
Real-time emission of performance updates provides the Capital Allocation Engine with instantaneous signals to freeze capital mid-drawdown or scale capital immediately upon proven calibrated conviction.

## 31. Decision-Centric Architecture Analysis
- **Option A (Worker-centric)**: Cannot granularly explain *why* a worker failed. Blurs strategies and regimes together.
- **Option B (Thesis-centric)**: Excludes the meta-layer of who approved or traded the thesis.
- **Option C (Decision-centric)**: SELECTED. By targeting the *Decision* (the moment a Thesis converted into execution), we natively capture the Worker, Strategy, Regime, and Calibration context simultaneously. It offers unparalleled Post-Mortem and Review reviewability.

## 32. Decision Performance Model
**`DecisionPerformanceRecord`**
The canonical Performance projection object.
- `decision_id`
- `thesis_id`
- `worker_id`
- `strategy_id`
- `regime_id`
- `outcome_reference`
- `stated_confidence`
- `realized_pnl`
- `calibration_score` (Brier evaluated specifically for this decision)

*Why canonical?* Because it acts as the unbreakable root node. Every subsequent slice of performance data is merely a `GROUP BY` query executed over the corpus of `DecisionPerformanceRecord`s.

## 33. Projection Hierarchy Model
The hierarchical cascade flows strictly from the Root:
1. `DecisionPerformanceRecord` (Root Read Model)
2. `WorkerPerformanceProfile` (Group by Worker)
3. `StrategyPerformanceProfile` (Group by Strategy)
4. `RegimePerformanceProfile` (Group by Worker + Regime)
5. `CalibrationProfile` (Group by Worker + Meta-dimensions)
6. `CapitalAllocationInputs` (Flattened multi-dimensional synthesis)

## 34. Replayability Architecture
**Authoritative Source**:
1. `Institutional Memory` (Kafka/S3 Event Store).
**Replay Process**:
The Performance Engine truncates all local databases. It re-streams `ThesisResolvedEvent` and `AttributionCalculatedEvent` from Institutional Memory. It deterministically rebuilds the `DecisionPerformanceRecord` table. Finally, it triggers a full recalculation of the Projection Hierarchy Model. 
**Projections Only**: 
Every single database table inside the Performance Engine boundary is a projection.

## 35. Future Architecture Compatibility
The `DecisionPerformanceRecord` acts as the Rosetta Stone for the Virtual Investment Firm.
- **Capital Allocation Engine**: Consumes real-time streams of Hierarchical Projections to size risk dynamically.
- **Review Engine**: Queries the `DecisionPerformanceRecord` directly to initiate Post-Mortems on historically terrible decisions.
- **Decision Journal**: The Web UI uses the exact same record structure to let workers audit their own historical biases.
