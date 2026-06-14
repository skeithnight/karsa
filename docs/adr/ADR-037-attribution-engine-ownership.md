# ADR-037: Attribution Engine Context Boundaries and Ownership

## Status
Approved

## Date
2026-06-14

## Context
Karsa requires a formal, systematic causal performance analysis and attribution engine to explain outcome results across the Virtual Investment Firm (VIF) loop:
**Research → Thesis → Decision → Outcome → Performance → Attribution → Review → Governance → Learning**.

Historically, the Attribution context was limited to token pricing and provider cost ledger balances (Attribution Engine Foundation in Sprint-22). This structural layout has gaps:
1. **No Causal Explanations**: We could trace how much a trade cost, but not *why* the underlying decision generated alpha or risk, or which component (worker, thesis version, market regime) contributed to the success.
2. **Capital Sizing Skew**: Without a dedicated causal attribution step, Capital Allocation would scale limits based on raw performance scores, risking funding strategies that succeed due to short-term market noise or luck.
3. **Database Contention**: Coupling attribution calculations directly to execution planners or portfolio databases violates Single Writer rules.

We need a dedicated causal attribution model within the Attribution Engine context with strict ownership boundaries.

## Decision
We enforce the following bounded context boundaries and ownership rules:

1. **Attribution Engine Ownership**:
   - The **Attribution Engine** is the sole writer and authority for:
     - `AttributionAnalysis` (Aggregate Root): Coordinates factor weight evaluations and recalculations.
     - `AttributionSnapshot` (Aggregate Root): Saves write-once, immutable point-in-time scores.
   - The Attribution Engine **does not** modify active thesis version states, execute trades, write portfolio limits, or enforce compliance policies directly.

2. **Integration Boundaries**:
   - **Performance Engine Integration**: Attribution consumes `DecisionEvaluatedEvent` scorecards to identify target performance values. Performance databases are read-only to Attribution.
   - **Capital Allocation Integration**: Capital Allocation consumes the final `AttributionCalculatedEvent` weights to scale sizing limits. Capital allocation limit parameters remain isolated in `db_capital`.
   - **Review Engine Integration**: The Review Engine reads attribution contribution scores to establish root failure causes during offline post-mortems.
   - **Single Writer Enforcements**: All inter-context interactions occur asynchronously via the event bus to prevent cross-database locking.

## Consequences
- **Decoupled causal explanations**: Downstream systems utilize attribution scores without locking the main execution path.
- **Accurate capital distribution**: Capital Allocation can reward components that consistently generate alpha.
- **Zero Cross-Locking**: Integration events ensure lock-free operations.
