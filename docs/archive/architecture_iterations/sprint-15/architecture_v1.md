# Sprint-15 Performance Engine Foundation - Architecture Revision v1

## 1. Executive Summary
The Sprint-15 Performance Engine Foundation transitions the platform from absolute financial attribution into longitudinal, probabilistic evaluation. While Attribution answers *who generated value*, Performance answers *who consistently generates value* under various market regimes and calibration pressures. This architecture aggressively sheds the traditional "ledger-as-aggregate" anti-pattern. Instead, it relies on high-throughput, horizontally scalable Event-Driven Projections and stateless rolling calculations to guarantee absolute replayability without Unit-of-Work write contention, perfectly positioning the system to feed the future Capital Allocation Engine.

## 2. Ownership Boundary Matrix
| Concept | Bounded Context | Description |
|---------|-----------------|-------------|
| `PerformanceProfile` | WP-15 Performance Engine | Statistical aggregation of a worker/strategy over time. |
| `CalibrationModel` | WP-15 Performance Engine | Evaluation of stated confidence vs realized accuracy. |
| `RegimeTracking` | WP-15 Performance Engine | Contextual tagging of performance metrics against market regimes. |
| `RegimeDefinition` | WP-## Regime Engine | (External) Upstream owner of `RegimeChangedEvent`. |
| `CapitalAllocation` | WP-## Capital Engine | (External) Downstream consumer of Performance metrics. |

## 3. Architecture Overview
The Performance Engine is fundamentally an asynchronous, high-throughput Analytical Projection Engine. It consumes `AttributionCalculatedEvent`, `AttributionReversedEvent`, `ThesisResolvedEvent`, and `RegimeChangedEvent`. Rather than locking aggregates on every financial tick, it utilizes a CQRS-style read-model architecture. Raw events are appended to a Performance Event Log. Background projection workers asynchronously calculate rolling windows (30D, 90D, Lifetime), confidence calibration, and regime-specific profiles, emitting `PerformanceSnapshotPublishedEvent`s periodically (e.g., daily) to inform Capital Allocation.

## 4. Domain Model
- **`PerformanceProjector`**: Domain service calculating rolling statistics.
- **`CalibrationEvaluator`**: Domain service comparing confidence intervals to hit-rates.
- **`RegimeSplitter`**: Domain service partitioning historical PNL by active regime.

## 5. Aggregate Design
**Zero Aggregates**
The Performance Engine contains NO traditional aggregates. Attempting to use a `WorkerPerformance` aggregate would result in massive UoW lock contention, as every fractional attribution globally would lock the worker's aggregate. Instead, Performance is modeled entirely as **Projections (Read Models)** built from the immutable event stream.

## 6. Value Objects
- **`PerformanceWindowIdentity`**: `target_identity`, `window_type` (30D, 90D, LIFETIME).
- **`RiskMetrics`**: `cumulative_pnl`, `drawdown_max`, `win_rate`, `sharpe_proxy`.
- **`CalibrationMetrics`**: `stated_confidence_avg`, `realized_accuracy`, `calibration_score` (-1.0 to 1.0).
- **`RegimeContext`**: `regime_id`, `regime_type` (BULL, BEAR, VOLATILE).

## 7. Event Contracts
- **`PerformanceSnapshotPublishedEvent`**:
  - `target_identity`
  - `snapshot_timestamp`
  - `lifetime_metrics`: `RiskMetrics`
  - `window_metrics`: Map of Window -> `RiskMetrics`
  - `calibration_metrics`: `CalibrationMetrics`
  - `regime_metrics`: Map of `RegimeContext` -> `RiskMetrics`

## 8. Application Services
- **`PerformanceEventIngestionService`**: Listens to external events and appends them to the internal Performance Event Log.
- **`PerformanceProjectionService`**: Cron-triggered or watermark-triggered service that sweeps the Event Log, recalculates the math statelessly, and updates the local Read Models.

## 9. Repositories
- **`PerformanceEventLogRepository`**: Append-only storage for normalized performance fragments.
- **`PerformanceReadModelStore`**: Fast-read projection store for the Web UI and downstream APIs.

## 10. Persistence Design
- **`performance_event_log` table**: Append-only ledger of normalized performance impacts (e.g., Target X gained $50 at T1).
- **`performance_projection` table**: Upsert-only JSONB cache of the latest `PerformanceSnapshotPublishedEvent`.

## 11. Integration Design
- **Inputs**: `AttributionCalculatedEvent`, `AttributionReversedEvent`, `ThesisResolvedEvent`, `RegimeChangedEvent`.
- **Outputs**: `PerformanceSnapshotPublishedEvent` (Daily or Epoch-based).

## 12. Sequence Diagrams
**Ingestion & Projection**:
1. `AttributionCalculatedEvent` arrives -> IngestionService appends to `performance_event_log`.
2. Daily Cron fires `PerformanceProjectionService`.
3. Service queries `performance_event_log` for a target.
4. Domain math calculates 30D/90D/Regime/Calibration.
5. Saves to `performance_projection`.
6. Emits `PerformanceSnapshotPublishedEvent` via Outbox.

## 13. State Diagrams
Projections have no lifecycle state. They are functionally derived pure representations of the event log at Time T.

## 14. Failure Handling
If a projection fails, it can be seamlessly discarded and recalculated from the underlying `performance_event_log`. No data loss is possible.

## 15. OCC Strategy
Because the system uses an Append-Only Event Log and Upsert Projections, OCC locks are fundamentally bypassed, maximizing ingestion throughput.

## 16. Scalability Analysis
Event ingestion is O(1) and horizontally scalable. Projection calculation is easily map-reduced across worker nodes by `target_identity`.

## 17. Security Analysis
Performance data determines capital allocation (real money). Emitted `PerformanceSnapshotPublishedEvent`s include deterministic hashing of the inputs to prevent database tampering.

## 18. Migration Strategy
Create `performance_event_log` and `performance_projection` tables.

## 19. Risks
- **Projection Lag**: Asynchronous projection means the Web UI might show T-1 data. This is an acceptable trade-off for eliminating lock contention.

## 20. ADR Decisions
- **ADR-15.01**: Zero-Aggregate Performance Domain. Performance tracking will use an Event-Sourced Projection architecture rather than UoW-locked Aggregates to eliminate write-contention bottlenecks.
- **ADR-15.02**: Epoch-Based Snapshotting. Performance metrics are published on scheduled epochs (e.g., daily) rather than synchronously on every attribution tick.

## 21. Architecture Challenges
- **Aggregate Boundaries**: Challenged and removed. Aggregates are wrong for highly-concurrent statistical tracking.
- **Ranking Scalability**: Challenged. Global ranking is extremely expensive to maintain synchronously. It must be an asynchronous Read Model sorting operation.

## 22. Architecture Delta Analysis
This architecture departs significantly from earlier, ledger-heavy assumptions by explicitly adopting pure CQRS. The Performance Engine acts entirely as a passive, mathematical observer.

## 23. Acceptance Criteria
1. Architecture completely avoids UoW locks on highly concurrent worker profiles.
2. Calibration properly correlates stated confidence from `ThesisResolvedEvent` against eventual PNL accuracy.
3. Market Regimes natively slice PNL into discrete risk buckets.

## 24. Final Verdict
**READY_FOR_ARCHITECTURE_REVIEW**

## 25. Performance Metric Model
Metrics move beyond raw PNL. 
- **Win Rate**: Positive PNL outcomes / Total Outcomes.
- **Risk-Adjusted Return (Sharpe Proxy)**: Average Return / Standard Deviation of Returns.
- **Drawdown**: Peak-to-trough decline tracked historically.

## 26. Performance Window Model
Windows (30D, 90D, 180D, 365D) are purely **Rolling Calculations** executed by the Projection Service against the temporal Event Log. They are NOT aggregates. If a calculation is requested for 30D, the service simply sums events with `timestamp > NOW - 30D`.

## 27. Ranking Model
Ranking is an asynchronous Read Model operation. Once `PerformanceSnapshotPublishedEvent`s are materialized into the `performance_projection` table, a secondary `GlobalRankProjector` applies dense-ranking (e.g., `RANK() OVER (ORDER BY sharpe_proxy DESC)`) and caches the leaderboard. It is entirely decoupled from the transactional ingestion path.

## 28. Regime Compatibility Model
The engine maintains a temporal mapping of Regimes (e.g., 2024-Q1 was BULL_MARKET). When rolling up metrics, the Engine groups `AttributionCalculatedEvents` by intersecting their timestamp with the active Regime. This allows the system to definitively state: "Worker A generates alpha in Bear markets but bleeds in Bull markets."

## 29. Confidence Calibration Model
Tracks `stated_confidence` (e.g., 80%) against the binary `outcome` (Hit/Miss).
- **Calibration Score**: The mathematical Brier Score (Mean Squared Error between forecast probability and actual outcome). A perfect score is 0.0. The future Capital Engine will mathematically discount capital given to workers with poor Brier scores, regardless of their raw PNL.

## 30. Capital Allocation Readiness Analysis
By flattening absolute dollars, regimes, calibration (Brier scores), and risk-adjusted trajectories into a single, daily `PerformanceSnapshotPublishedEvent`, the future Capital Allocation Engine has a completely deterministic, computationally lightweight menu of inputs to size virtual portfolios. The architecture is perfectly primed.
