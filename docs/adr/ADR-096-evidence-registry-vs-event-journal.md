# ADR-096: Evidence Registry vs Event Journal Boundary

- **Status**: Accepted
- **Date**: 2026-06-17
- **Supersedes**: N/A
- **Superseded By**: N/A

## Context
With the introduction of the Evidence Registry, there was a severe risk of blurring the lines with the CQRS Event Journal, potentially turning the Evidence Registry into a secondary event store and destroying the single-source-of-truth.

## Decision
We establish explicit, non-overlapping boundaries:
1. **Event Journal**: The absolute System of Record for internal VIF state transitions (Decisions, State changes). It is append-only and replayable.
2. **Evidence Registry**: The absolute System of Record for external facts and payloads. It stores content-addressable hashes (`evidence_urn`) of normalized provider data.

## Consequences
1. **Data Bloat Prevention**: The Event Journal remains lean. It only stores the `evidence_urn` pointer, never the 50MB raw earnings report payload.
2. **Provider Corrections**: If a data provider republishes corrected historical data, the Evidence Registry stores the new payload and generates a *new* hash. The old hash remains permanently accessible to guarantee the integrity of past decisions.
3. **Audit Matrix**: Post-Mortem and Attribution engines construct their chronological timeline exclusively from the Event Journal, but fetch the exact historical context by dereferencing the `evidence_urn`s from the Evidence Registry.
