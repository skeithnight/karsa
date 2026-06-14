# ADR-029: Thesis Engine Bounded Context and Ownership Boundaries

## Status
Approved

## Date
2026-06-14

## Context
Karsa’s target Virtual Investment Firm (VIF) architecture requires an authoritative, audit-ready context to manage investment theses. A thesis captures the logical, qualitative, and mathematical rules (including invalidation limits) that justify risk allocations and model deployments.

Historically, thesis concepts were loosely mapped inside code comments, research backtests, or portfolio allocation scripts. This scattering creates severe issues:
1. **No Single Source of Truth**: Different systems disagree on active hypothesis constraints.
2. **Loss of Audit Trail**: Changing a thesis rule breaks the historical record, rendering replays of past decisions non-deterministic.
3. **Coupling**: The core investment logic becomes entangled with performance stats, system execution traces, or narrative decision journals.

To resolve these issues, we must establish a standalone **Thesis Engine Bounded Context** with strict, clean ownership boundaries.

## Decision
We enforce the following bounded context boundaries:

1. **Thesis Engine Ownership**:
   - The **Thesis Engine** is the sole authority and writer of:
     - `ThesisDefinition`: Metadata and logical headers tracking a family of theses over time.
     - `ThesisVersion`: Immutable snapshots containing invalidation criteria, horizons, confidence scores, risks, assumptions, and hypotheses.
     - `ThesisExecutionBinding`: Entity bridging a version to a concrete deployment (portfolio, strategy, status, and limits).
     - Thesis state transitions (`DRAFT` → `REVIEW` → `ACTIVE` → `CANARY` → `INVALIDATED` → `FAILED` → `ARCHIVED`).
2. **Context Separation Boundaries**:
   - **Research Engine Separation**: The Research Engine owns backtest simulations, parameter searches, and Parquet execution logs. A `ThesisVersion` links back to Research via a read-only reference to `research_run_id` but never modifies research state.
   - **Decision Journal Separation**: The Decision Journal owns narrative, qualitative reasoning, and textual logs written by operators during decisions. The Thesis Engine defines the structured mathematical/invalidation hypothesis referenced by the journal.
   - **Performance Engine Separation**: The Performance Engine evaluates thesis accuracy, hit rates, and confidence calibrations over time. It does **not** write to `db_thesis`. Instead, it reads thesis definitions and versions to construct a read-side `ThesisPerformanceProjection` and writes Brier / accuracy scores to its own database (`db_performance`). The Thesis Engine reads this projection asynchronously to check invalidation criteria limits.
   - **Capital Allocation Engine Separation**: The Capital Allocation Engine owns setting risk and allocation limits. It does so by writing target limits to `ThesisExecutionBinding` records, leaving the core `ThesisVersion` rules untouched. It has no write hooks into the core version definitions.
   - **Review Engine Separation**: The Review Engine conducts post-mortems and audits the `Research -> Thesis -> Decision -> Outcome -> Review` lifecycle. It **cannot** directly mutate thesis aggregates, invalidate versions, supersede them, or write new versions. It is restricted to **recommend-only** actions, logging results in `ReviewSession` aggregates inside `db_review`.
   - **Attribution Engine Separation**: The Attribution Engine records financial execution costs ($ USD) mapped to a `thesis_version_id` and the specific `binding_id`. The Thesis Engine does not compute or manage token costs.
   - **Observability Platform Separation**: Observability spans and correlation contexts store read-only `thesis_id`, `thesis_version_id`, and `binding_id` references to enable tracing. No thesis rule definitions reside in tracing databases.

## Consequences
- **Strict Separation of Concerns (SoC)**: Changes to portfolio policies, metric definitions, or execution logs do not affect core investment hypotheses.
- **Deterministic Audit Trail**: Downstream engines can retrieve the exact thesis rule in effect during any past decision by referencing `thesis_version_id`.
- **Zero Coupling**: Subsystems interact strictly using identity keys (`thesis_id`, `thesis_version_id`, `research_run_id`, `outcome_id`), preventing database write amplification or transaction locks across bounded contexts.
- **Strict Writer Rule Enforcement**: Thesis Engine remains the single source of writes for its aggregates, eliminating transactional overlaps from the Review or Performance Engines.
