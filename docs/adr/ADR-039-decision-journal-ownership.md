# ADR-039: Decision Journal Context Boundaries and Ownership

## Status
Approved

## Date
2026-06-14

## Context
Karsa requires a formal, centralized, and audited pre-outcome reasoning registry to support the Virtual Investment Firm (VIF) loop:
**Research → Thesis → Decision (Journaled) → Outcome → Performance → Review → Governance → Learning**.

Historically, investment decisions and prompt queries were executed without formal, immutable, pre-outcome justification logs. This structural gap creates several architectural issues:
1. **Hindsight Bias and Contamination**: LLM agents or human managers can retroactively adjust their reasoning or baseline assumptions once execution outcomes are realized, making model calibration and prediction error analysis unreliable.
2. **Missing Prediction Baseline**: Without a static capture of model confidence bounds and rationale *before* execution, the Performance Engine cannot evaluate the delta between expected and actual outcomes (prediction error).
3. **Database Pollution**: Coupling reasoning logs directly to execution planners or portfolio tables violates context boundaries.

We need a dedicated **Decision Journal Bounded Context** with strict boundaries and ownership rules.

## Decision
We enforce the following bounded context boundaries and ownership rules:

1. **Decision Journal Ownership**:
   - The **Decision Journal** is the sole writer and authoritative subsystem for the `DecisionJournal` (Aggregate Root), which represents an immutable, write-once ledger entry.
   - Separate `DecisionSnapshot` aggregates are retired to avoid aggregate inflation. The point-in-time model parameters and environmental telemetry are stored as a nested `DecisionContext` value object, offloaded to an immutable object store and referenced via SHA-256 hash.
   - The Decision Journal Engine **does not** execute trades, write portfolio allocations, or define compliance policies.

2. **Integration Boundaries**:
   - **Thesis Engine Integration**: Ingests active thesis versions and prompts during journal assembly. Thesis databases are read-only to the Journal.
   - **Performance Engine Integration**: Performance Engine reads pre-outcome confidence parameters from the journal to compute scorecard prediction error rates (e.g. Brier scores).
   - **Attribution Engine Integration**: Attribution reads the journal's environmental context snapshot to analyze causal factor contributions.
   - **Post-Mortem Engine Integration (Future)**: Post-Mortem reads pre-outcome journal logic to detect hindsight bias or reasoning drift.
   - **Single Writer Enforcements**: All inter-context interactions occur asynchronously via events to prevent cross-database locking.
   - **Hindsight Contamination Verification**: Downstream engines (Performance, Attribution) MUST validate that the journal entry's `created_at` timestamp is strictly prior to the trade execution's `started_at` timestamp. Any entry timestamped post-execution is rejected.

## Consequences
- **Decoupled pre-outcome reasoning**: Downstream contexts query journal entries without locking the active trading path.
- **Hindsight Bias Prevention**: Immutability rules and strict downstream timestamp audits guarantee that pre-outcome reasoning cannot be retroactively updated or contaminated.
- **Clean Prediction Baselines**: Provides the baseline against which performance is evaluated.
- **Simplified Domain Boundary**: Eliminating the secondary `DecisionSnapshot` aggregate prevents aggregate inflation.
