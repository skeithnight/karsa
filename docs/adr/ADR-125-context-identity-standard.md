# ADR-125: Context Identity Standard

## Status
Accepted

## Context
The Karsa Validation Platform comprises five highly distinct bounded contexts. To ensure event stream traceability, replay determinism, and UI aggregation, a standardized identity format must be mandated across all domain payloads.

## Decision
We mandate the UUIDv4 string format for all primary identifiers. Identifiers MUST be strictly owned by the bounded context that first introduces the concept.

### Identity Specifications

*   **forecast_id**: Uniquely identifies a singular market prediction. Owned and created by the Discovery/Forecast domains.
*   **capability_id**: Uniquely identifies an intelligence-generating model/human. Owned and created by the Provider/Discovery domains.
*   **thesis_id**: Uniquely identifies a macro narrative. Owned by the Thesis domain.
*   **lineage_id**: Identifies the specific Attribution DAG graph. Owned and created by the Attribution Engine.
*   **snapshot_id**: Identifies a point-in-time Firm Health rendering. Owned and created by the Firm Health Dashboard context.
*   **assessment_id**: Identifies a Trust Engine vector calculation. Owned and created by the Trust Engine.

### Propagation Rules
Identity keys must be propagated structurally via the `event_journal`. They form the correlation and causation IDs for downstream projections.

### Immutability Rules
Once generated and committed to the Event Store, an Identity is completely immutable. Re-calculations or versions append to the stream rather than replacing the Identity.

### Replay Rules
During a replay, the `stream_id` sequencer operates deterministically against these identities. The identities MUST NOT be re-generated during replay; the raw payloads natively carry them.
