# Sprint 3 Remediation & Technical Debt

## Closed Debt
- FSM Abort Support: Cleanly integrated without duplicate state management.
- Policy Immutability: Re-reading policies during crash loops is officially prevented.

## Current Technical Debt (Deferred)
- **Multi-agent budget overrides**: Single static policy applies globally.
- **Streaming token kill switches**: Limits check occurs only pre and post logic loops; no active socket termination logic exists for runaway streaming providers.
- **Governance metrics engine redesign**: Global `.karsa/governance_metrics.json` must eventually be replaced by a distributed map-reduce job on the event lake.
- **Large EventRegistry refactors**: Deserializer still tightly couples event types in `persistence.py`.
