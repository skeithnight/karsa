# ADR-048: CIO Decision and Orchestration Model

## Status
Approved

## Date
2026-06-14

## Context
Designing the decision orchestrator for the Virtual Investment Firm (VIF) requires a model that handles conflicting recommendations, resolves concurrency, and ensures that a portfolio configuration from 5 years ago can be reconstructed with absolute audit integrity. We must evaluate direct worker allocations versus hierarchical models, and determine whether the CIO context requires mutable aggregate roots.

## Decision
We implement the following CIO decision and orchestration model:

1. **Immutable Append-Only Decision Ledger**:
   - The CIO context contains **zero mutable aggregate roots**. Both decisions and active portfolio configurations are written to write-once ledger tables (`cio_decisions` and `portfolio_states`). 
   - State updates append new rows to the ledger. This design completely eliminates Optimistic Concurrency Control (OCC) write-conflict overhead.

2. **Hierarchical Portfolio Construction**:
   - We implement the `Portfolio -> Strategy -> Thesis -> Decision -> Worker` model. 
   - This ensures that every worker's active trading limits are explicitly linked back to the authorizing CIO decision record, and that the decision links back to the active thesis version.

3. **Decision Authority Matrix**:
   - **Permitted Actions**: The CIO Engine can Approve/Reject allocations, Promote/Retire theses, Activate/Retire workers, Quarantine workers, and Request Governance exceptions.
   - **Prohibited Actions**: The CIO Engine cannot override active Governance policies or breaches. It can override Review recommendations or Attribution weights by logging an explicit justification in the decision ledger.

4. **Precedence-Based Conflict Resolution**:
   - Conflicting recommendations (e.g. Bull BUY vs. Bear SELL vs. Governance exceptions) are resolved using a strict precedence pipeline:
     1. **Governance HARD_STOP**: Cuts allocation to 0.0 (Status: Ineligible).
     2. **CIO Override Decision**: Applies manual strategic override.
     3. **Governance SOFT_LIMIT / Exception**: Caps limits.
     4. **Capital Allocation Model**: Applies recommended returns/risk ratios.
     5. **Review Engine Multipliers**: Adjusts according to review score.
     6. **Decision Journal Brier Score**: Calibrates according to prediction quality.

## Consequences
- **Lock-Free Operation**: Telemetry and decision ingestion remain highly scalable without OCC locking.
- **Traceability**: Audit paths recursively link workers back to theses, decisions, and research pipelines.
- **Fail-Safe Compliance**: Governance rules automatically override and contain strategic allocations.
