# ADR-031: Performance Engine Context Ownership and Boundaries

## Status
Approved

## Date
2026-06-14

## Context
Karsa requires an authoritative, audit-ready context to evaluate decision and strategy performance. Historically, accuracy scoring, hit rates, confidence calibration, and benchmark comparisons were scattered across different contexts (e.g. within research scripts, allocation engines, or logging streams).

This scattering introduces severe defects:
1. **Overlap & State Corruption**: Allocation engines or review tools updating accuracy records directly on the trading aggregates violates the Single Writer principle.
2. **Coupling**: Scoring logic becomes blocked by database transaction locks on active execution tables, leading to write amplification.
3. **No Replay Reproducibility**: Changing metric calculation logic retroactively alters historical performance evaluations, breaking the audit trail.

To resolve these defects, we must define a dedicated **Performance Engine Bounded Context** with strict, clean ownership boundaries.

## Decision
We enforce the following bounded context boundaries:

1. **Performance Engine Ownership**:
   - The **Performance Engine** is the sole authority and writer of:
     - `DecisionEvaluation`: The core aggregate root representing Karsa's primary unit of learning. It is immutable once finalized.
     - `EvaluationSnapshot`: Frozen, immutable history of a decision evaluation.
     - `PerformanceEvaluation` (Projection): Materialized read-side scorecard tracking cumulative metrics.
     - `ThesisExecutionBindingPerformanceProjection` (Projection): Read-side scorecard for active allocations.
     - Benchmark definitions and index comparisons (`BenchmarkComparison`).
     - Calibration statistics and tables (`CalibrationMeasurement`).
   - The Performance Engine **does not** execute trades, calculate execution costs, own telemetry logs, or make capital allocation decisions.
2. **Context Separation Boundaries**:
   - **Attribution Engine Separation**: The Attribution Engine owns financial execution costs. The Performance Engine reads cost projections but never mutates attribution records.
   - **Thesis Engine Separation**: The Thesis Engine owns structured hypotheses and version states. The Performance Engine reads thesis versions to retrieve validation boundaries, outputting its findings to the read-side `ThesisExecutionBindingPerformanceProjection`.
   - **Review Engine Separation**: The Review Engine owns qualitative post-mortems and `LearningFeedback` aggregates. The Performance Engine provides quantitative metrics (via `DecisionEvaluation` and `DecisionEvaluatedEvent`) which the Review Engine reads. The Review Engine writes subjective findings to `db_review`, referencing the target `evaluation_id` without write hooks into Performance database tables.
   - **Governance Engine Separation**: The Governance Engine enforces risk policy compliance. The Performance Engine provides input performance statistics (e.g. invalidation rates) to governance PDP/PEP blocks, but does not execute policy updates.
   - **Capital Allocation Engine Separation**: The Capital Allocation Engine owns setting risk and allocation limits on `ThesisExecutionBinding` records. It reads performance rankings from the `ThesisExecutionBindingPerformanceProjection` to adjust position ceilings, but has no write access to the performance scores.
   - **Observability Platform Separation**: Observability tracks spans and traces. Performance Engine consumes `ExecutionOutcome` (a shared contract integration event produced by Capability/Telemetry) via event streaming, but no performance stats reside in tracing databases.

## Consequences
- **Strict Separation of Concerns (SoC)**: Changes to portfolio policies, metric definitions, or execution logs do not affect core investment hypotheses.
- **Deterministic Audit Trail**: Downstream engines can retrieve the exact decision evaluation rule in effect during any past decision by referencing `evaluation_id`.
- **Zero Coupling**: Subsystems interact strictly using identity keys (`decision_id`, `thesis_version_id`, `binding_id`), preventing database write amplification or transaction locks across bounded contexts.
- **No Redesign Required**: The decoupling of the qualitative review and capital allocation engines ensures that future updates in those contexts will not require redesigning the Performance Engine.
