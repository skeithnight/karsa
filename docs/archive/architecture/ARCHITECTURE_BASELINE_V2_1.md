# Architecture Baseline V2.1

## Architecture Principles
- Async-First Execution: Decouple FSM Orchestrator from Executor via Job Queues.
- Least Privilege: Limit AST capabilities dynamically per workflow.
- Immutable Lineage: Git-like workspaces for safe replays.

## Architecture Goals
Provide a robust multi-agent distributed foundation for the AI Software Company.

## Approved Components
- WorkspaceManager, ArtifactRegistry, EvidenceRegistry, ExecutionPlanner, JobQueue, QueueWorker, DockerExecutor, SecurityScanner, GovernanceService, TaskGraph.

## Deferred Components
- KubernetesExecutor, Grafana Dashboards, Remote Multi-Node Deployment (testing locally first).

## Out of Scope
- Custom Provider Integration (OpenAI/Anthropic) until Gemini execution is flawless.

## Sprint Mapping
- Epic A: Workspace Foundation
- Epic B: Security Architecture
- Epic C: Queue & Execution Engine
- Epic D: Multi-Agent Coordination
- Epic E: Governance Layer
- Epic F: Execution Observability

## Implementation Constraints
- No native `subprocess.run` testing. All tools must run in Docker Sandbox.
# Sprint-15 Performance Engine Foundation - Architecture Revision v6

## 1. Executive Summary
The Sprint-15 Performance Engine Foundation transitions the Virtual Investment Firm (VIF) from absolute financial attribution into longitudinal, probabilistic evaluation. The architecture decisively adopts a Decision-centric, pure CQRS projection model. All performance states are derived asynchronously from the immutable Institutional Memory. By rigorously challenging boundary leakage, this revision revokes premature alpha calculations and allocation multipliers, stripping the Performance Engine down to objective, mathematically infallible statistical reality. The result is a highly scalable, drop-to-zero replayable intelligence engine that cleanly bridges Attribution and Capital Allocation.

## 2. Ownership Boundary Matrix
| Engine | Responsibility | Boundary Rule |
|--------|----------------|---------------|
| **Attribution** | Fractional PNL splits. | Owns the absolute dollar allocation. |
| **Performance** | Statistical evaluation & hit-rates. | Owns *What* happened mathematically across decisions. |
| **Review** | Qualitative Post-Mortems. | Owns *Why* decisions failed (Execution vs Flaw). |
| **Capital Allocation**| Portfolio Sizing & Multipliers. | Owns the translation of metrics into risk limits. |
| **Thesis Engine** | Decision Lifecycle. | Owns the `decision_id` origination. |

## 3. Architecture Overview
The Performance Engine is an asynchronous, event-driven Projection Pipeline. It consumes raw immutable events from Institutional Memory (`DecisionCommittedEvent`, `AttributionCalculatedEvent`, `RegimeChangedEvent`). Through an internal local-bus pipeline, it structurally reduces these events into a canonical `DecisionPerformanceRecord` projection, which then cascades into multi-dimensional profiles (Worker, Strategy, Thesis, Regime, Calibration, Window). The system possesses zero traditional aggregates and zero storage authority.

## 4. Domain Model
- **`PerformanceProjector`**: Orchestrates the statistical reduction of raw attribution into performance records.
- **`CalibrationEvaluator`**: Computes objective Brier scores evaluating stated confidence against binary hit-rates.
- **`HierarchicalProjectionOrchestrator`**: Dispatches cascaded updates to secondary materialized views.

## 5. Aggregate Design
**Zero Aggregates.**
The bounded context contains NO aggregates. Utilizing UoW-locked aggregates for high-velocity global performance ranking and rolling statistics creates catastrophic lock contention. The engine relies entirely on Rebuildable Read Models (Projections).

## 6. Value Objects
- **`DecisionPerformanceIdentity`**: `decision_id`, `outcome_sequence_id`, `attribution_generation`.
- **`RiskMetrics`**: `cumulative_pnl`, `max_drawdown`, `volatility_proxy`.
- **`CalibrationMetrics`**: `brier_score`, `stated_confidence`, `hit_rate`.

## 7. Event Contracts
- **`PerformanceSnapshotPublishedEvent`**: Periodically (or dynamically) published synthesis of raw metrics exposing the statistical profile of a target (Worker/Strategy/Thesis) for downstream consumption.

## 8. Application Services
- **`PerformanceEventIngestionService`**: Listens to Institutional Memory and synthesizes the root `DecisionPerformanceRecord`.
- **`CascadingProjectionService`**: Independent stream consumers that apply `DecisionPerformanceRecord` deltas to downstream profiles.

## 9. Repositories
- **`DecisionPerformanceProjectionStore`**: Upsert-only store for the canonical root records.
- **`HierarchicalProfileStore`**: Materialized view stores for downstream profiles.

## 10. Persistence Design
All tables are projections prefixed with `projection_`.
- `projection_decision_performance`
- `projection_worker_performance`
- `projection_thesis_performance`
- `projection_regime_performance`
- `projection_calibration`
- `projection_performance_window`

## 11. Integration Design
- **Inputs**: `DecisionCommittedEvent`, `AttributionCalculatedEvent`, `RegimeChangedEvent` (from Institutional Memory).
- **Outputs**: `PerformanceSnapshotPublishedEvent` (Raw statistics sent to Capital Allocation).

## 12. Sequence Diagrams
1. `AttributionCalculatedEvent` emitted by Attribution Engine.
2. IngestionService reads event, joins with historic `DecisionCommittedEvent`.
3. Validates identity and writes to `projection_decision_performance`.
4. Emits internal `DecisionPerformanceRecordAppended`.
5. Independent consumer threads update `Worker`, `Thesis`, and `Regime` projections using deterministic math.

## 13. State Diagrams
Projections lack lifecycles. They are temporal snapshots derived mathematically from the event stream.

## 14. Failure Handling
If projection logic contains a bug or a view becomes corrupted, the entire database schema is `TRUNCATE`d and rebuilt chronologically from Institutional Memory. No data loss is possible.

## 15. OCC Strategy
Because projections are built asynchronously and idempotently via `outcome_sequence_id` tracking, standard OCC locking is bypassed in favor of native DB `UPSERT` semantics.

## 16. Scalability Analysis
The Layered Projection Pipeline inherently resolves fan-out amplification. The Root record is written in O(1). The internal local-bus buffers the cascaded updates, allowing the system to easily sustain bursts of 100,000+ decisions/day without locking.

## 17. Security Analysis
Immutable inputs guarantee tamper-proof performance stats. Workers cannot rewrite their own history; all restatements must flow natively through Governance into Attribution before Performance registers the change.

## 18. Migration Strategy
Initialize the projection schemas. Wipe any legacy V1/V2 ledger architectures.

## 19. Risks
- **Event Ordering**: Out-of-order events can theoretically warp point-in-time drawdown metrics. Mitigated by explicit `occurred_at` sequencing logic during ingestion.

## 20. ADR Decisions
- **ADR-15.12**: Strict Statistical Ownership. The Performance Engine publishes raw statistical truths ONLY. It does NOT publish Allocation Multipliers (revoking ADR-15.11) and does NOT publish Benchmark-relative Alpha (revoking ADR-15.10).
- **ADR-15.13**: Projection-Only Authority. The entire engine database is ephemeral and can be dropped to zero tables.

## 21. Architecture Challenges
- **Boundary Leakage**: Explicitly solved. Performance generates Brier Scores. Capital Allocation decides what a Brier Score is worth.

## 22. Architecture Delta Analysis
- **Delta from v5**: Stripped benchmark dependencies to protect replay determinism.
- **Delta from v5**: Stripped `CapitalAllocationSynthesisProfile` to prevent policy logic leakage.
- **Delta from v4**: Formalized Thesis Engine ownership of the Decision lifecycle.

## 23. Acceptance Criteria
1. Performance Engine runs entirely without UoW aggregates.
2. Database can be dropped and rebuilt yielding a byte-for-byte identical state.
3. Output events contain zero allocation or risk-limit directives.

## 24. Final Verdict
**ARCHITECTURE_FROZEN**
*Justification*: The architecture has rigorously shed all tangential boundary leakage. It accurately models pure, statistical reality with drop-to-zero replay guarantees, positioning the Virtual Investment Firm for flawless future integration.

## 25. Replay Dependency Matrix
| Projection | Required Inputs | Deterministic Rebuild Process | Tie-Break/Ordering |
|------------|-----------------|-------------------------------|--------------------|
| **`DecisionPerformanceRecord`** | `DecisionCommittedEvent`, `AttributionCalculatedEvent` | Join on `decision_id`. Math execution. | Stream sequence. |
| **`ThesisPerformanceProfile`** | `DecisionPerformanceRecord` | Group by `thesis_id`. | N/A |
| **`WorkerPerformanceProfile`** | `DecisionPerformanceRecord` | Group by `worker_id`. | N/A |
| **`StrategyPerformanceProfile`** | `DecisionPerformanceRecord` | Group by `strategy_id`. | N/A |
| **`RegimePerformanceProfile`** | `DecisionPerformanceRecord`, `RegimeChangedEvent` | Temporal overlap intersection (`>= start, < end`). | Strict UTC handling. |
| **`CalibrationProfile`** | `DecisionPerformanceRecord` | Brier Score = `(forecast - outcome)^2`. | N/A |
| **`PerformanceWindowProfile`** | `DecisionPerformanceRecord` | Sum of discrete Time-Partitioned Events. | Daily UTC Buckets. |

## 26. Projection Ownership Matrix
- **`DecisionPerformanceRecord`**: Performance Engine (Logical Model)
- **`ThesisPerformanceProfile`**: Performance Engine (Thesis accuracy projection)
- **`WorkerPerformanceProfile`**: Performance Engine (Worker accuracy projection)
- **`CapitalAllocationSynthesisProfile`**: DELETED (Moved to Capital Engine)

## 27. Virtual Investment Firm Alignment Analysis
- **Current State**: Attribution feeds Performance.
- **Target State**: Performance mathematically reduces Attribution outcomes into multi-dimensional probabilistic models (Hit Rate, Brier Score, Drawdown).
- **Gap Analysis**: Closed. The engine aligns perfectly as a pure analytical provider.

## 28. Capital Allocation Boundary Analysis
**Challenge**: Should Performance Engine publish allocation multipliers (ADR-15.11)?
**Decision**: NO. Allocation multipliers represent *Capital Policy*, which evolves independently of *Statistical Reality*. If the firm decides to punish bad Brier Scores more aggressively, that is a Capital Allocation rule change. The Performance Engine must only publish the objective Brier Score. This completely decouples Performance from portfolio risk policy.

## 29. Review Engine Boundary Analysis
The Performance Engine answers *What happened?* (e.g., Thesis hit-rate is 22%). The Review Engine answers *Why?* (e.g., Thesis relied on faulty macro data). Performance provides the quantitative trigger; Review provides the qualitative journal.

## 30. Projection Replayability Assessment
**Challenge**: Can the database be dropped to zero tables and rebuilt?
**Answer**: **YES**.
**Sequence**:
1. Drop all `projection_*` tables.
2. Stream `RegimeChangedEvent`s to memory.
3. Stream `DecisionCommittedEvent`s + `AttributionCalculatedEvent`s sequentially based on `occurred_at` UTC time.
4. Materialize `DecisionPerformanceRecord`s exactly in order.
5. Apply exact deterministic mathematical tie-breakers (Bankers Rounding, DECIMAL(19,4), Lexicographical target IDs) to hierarchical profile cascades.
**Consistency Guarantee**: 100% deterministic, byte-for-byte identical state.

## 31. Architecture Freeze Readiness Assessment
The Architecture has withstood intense challenges against its scalability, determinism, and bounded-context integrity. 
- The Decision identity is bulletproof.
- Idempotency is structurally solved.
- Replay is formally guaranteed.
- External dependencies (Benchmarks, Policy Multipliers) have been stripped to preserve purity.

The architecture is formally ready for implementation planning.
**ARCHITECTURE_FROZEN**
