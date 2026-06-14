# ADR-041: Post-Mortem Engine Context Boundaries and Ownership

## Status
Approved

## Date
2026-06-14

## Context
As Karsa evolves toward the Virtual Investment Firm (VIF) target architecture, we need a dedicated subsystem for investigating failure events, identifying root causes, and propagating lessons. Historically, qualitative reviews were handled ad-hoc, and there was no systematic way to quarantine failing models or dynamically adjust limit sizes based on post-event analysis.

Adding this capability requires a dedicated **Post-Mortem Engine Bounded Context**. To prevent context bloat and overlap with existing engines, we must define strict ownership and integration boundaries.

## Decision
We enforce the following bounded context boundaries and ownership rules:

1. **Post-Mortem Engine Ownership**:
   - The **Post-Mortem Engine** is the sole writer and authoritative subsystem for the `PostMortemRecord` (Immutable Write-Once Ledger Entry), which represents the historical record of a failure event. The context contains zero mutable aggregate roots.
   - It **does not** calculate general performance metrics (owned by Performance), calculate causal contribution factors (owned by Attribution), define pre-outcome reasoning (owned by Decision Journal), or enforce real-time limits (owned by Governance).

2. **Decoupled Integration Boundaries**:
   - **Performance Engine Integration**: Ingests performance scorecard deviations as trigger events. Performance databases are read-only to Post-Mortem.
   - **Attribution Engine Integration**: Post-Mortem reads statistical attribution factors to guide root-cause weighting.
   - **Decision Journal Integration**: Post-Mortem queries the pre-outcome reasoning logs (via `decision_id`) to analyze model assumptions.
   - **Event-Driven Learning Loops**: Lessons learned are propagated asynchronously via the event bus using the `PostMortemRecordCreatedEvent`. Other contexts (Thesis Engine, Governance Engine, Research Engine, Capital Allocation) listen to these events and apply updates internally. Post-Mortem never mutates other context databases directly.

## Consequences
- **Decoupled Failure Analysis**: Downstream engines process lessons out-of-band without affecting active trading paths.
- **Zero Mutative Coupling**: All cross-context state changes are event-driven, protecting boundary integrity.
- **Eliminated Redundancies**: Ownership of statistical correlation, quantitative error, and qualitative post-mortems is strictly isolated.
