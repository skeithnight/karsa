# ADR-017: Capability Execution Contracts and Replay Decoupling

## Status
Approved

## Date
2026-06-14

## Context
Karsa mandates reproducible workflow replays. However, most capability executions (such as LLM inference, web search, or code compilation) are inherently non-deterministic or side-effect heavy. Re-executing capabilities physically during a replay:
1. Deviates from the original execution trajectory due to LLM stochasticity or changing external API results.
2. Incurs high and redundant operational costs.
3. Mutates external system states.
4. Breaks provider agnosticism if execution is tied to active provider credentials during replays.

We must decouple the logical capability contract from the physical execution, ensuring deterministic replays.

## Decision
We implement the following architecture:
1. **Separation of Contract and Adapter**: The Capability Engine only knows about `CapabilityDefinition` and `ExecutionContract` (input/output JSON schemas, preconditions). It delegates physical execution to a registration-bound `ProviderAdapter`.
2. **Deterministic Replay (Mock Injection)**: During workflow replays, the Capability Engine operates in `REPLAY` mode. The execution pipeline intercepts requests, bypasses the active `ProviderAdapter`, and fetches the historical results from the `EvidenceRegistry` using a unique `execution_id`.
3. **Immutable Telemetry & Execution Evidence**: Every live capability execution publishes an `ExecutionEvidence` record containing:
   - `execution_id`, `correlation_id`, `causation_id`.
   - The exact input/output payloads.
   - Resource metrics (CPU/memory/duration) and token costs.
   - File artifacts generated.
4. **Job Serialization**: The Capability Engine compiles execution requests into a serialized `CapabilityJob` containing the target workspace `snapshot_id`, `branch_id`, and input payload. This job is dispatched to distributed queue workers, ensuring execution can occur on any node without local state.

## Consequences
- **Replayability**: Ensures 100% deterministic, byte-for-byte identical workflow replay.
- **Provider Agnosticism**: Simplifies unit and integration testing by mocking provider adapters.
- **Traceability**: All outputs are frozen in the `EvidenceRegistry`, creating a permanent, tamper-proof audit trail.
- **Limitation**: If a replay branches (i.e. input changes), the system must transition out of `REPLAY` mode to `LIVE` mode for that branch, terminating the mock injection.
