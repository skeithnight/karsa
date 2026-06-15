# ADR-067: Telemetry Sampling and Fidelity

## Status
Accepted

## Context
Ingesting 100M+ full-fidelity telemetry events daily into PostgreSQL destroys the SSD endurance (TBW) on Lenovo Tiny home-lab nodes via extreme write amplification. 

## Decision
We establish a tripartite fidelity model:
1. **Full Fidelity Events**: Only strict business events (Thesis, Decision, Outcome, Performance, Attribution, Governance) are 100% captured. These are legally bound ledgers and exempt from pruning.
2. **Aggregated Metrics**: Extreme high-volume signals (e.g., capability inference chunks) are NEVER stored raw. They are aggregated in-memory and flushed to Postgres as 1-minute `SummaryStat` snapshots.
3. **Sampled Traces**: Operational execution traces (e.g., worker generic step logs) are sampled at 1% probabilistically. If an error occurs, the worker forces a 100% trace capture for that specific causation chain dynamically.

## Consequences
* SSD write amplification is reduced by ~95%.
* Home lab hardware lifecycle is extended to multiple years.
* Real-time visibility remains high due to aggregated metrics, while debugging depth is preserved via error-triggered full traces.
