# ADR-038: Causal Attribution and Contribution Model

## Status
Approved

## Date
2026-06-14

## Context
Designing a factor-attribution engine that processes up to 100M+ evaluations per day requires clean context boundaries, deterministic replay stability, and strict factor weight math. The design must address:
1. **Aggregate Inflation**: Having separate aggregates for each dimension or snapshot version creates database table bloat and write lock hotspots during concurrent evaluations.
2. **Attribution Skew**: Inconsistent scoring models can bias results (e.g. attributing all success to workers and failure to market conditions).
3. **Replay Integrity**: If historical pricing or regime states are updated, re-running historical audits must yield the exact attribution weights calculated at that timestamp.

## Decision
We implement a **Versioned Immutable Ledger Entry model** instead of mutable aggregate roots for Karsa's attribution calculations:

1. **Decoupled Architecture and Classification**:
   - The Attribution context contains **zero mutable aggregate roots**, avoiding transactional lock contention entirely.
   - **`AttributionAnalysis`** is classified as a **Versioned Immutable Ledger Entry** (not a mutable aggregate). Every calculation or recalculation run appends a write-once record with an incremented version (e.g. `version = 2`), bypassing OCC.
   - **`AttributionSnapshot`** is retired as a separate aggregate root. Since ledger records are already immutable, snapshots are merged directly into the versioned ledger database.
2. **Strict Normalization Rules**:
   - Total contribution weights across all dimensions within an evaluation must sum exactly to 1.0 (or 100% normalized weight). This guarantees mathematical consistency.
3. **Cryptographic Snapshot Verification**:
   - Every ledger record is saved with a SHA-256 integrity hash computed over the serialized contribution vector.
   - Auditing re-calculates the historical weights using the raw event logs active at the target timestamp and validates the result against the snapshot hash, guaranteeing replay determinism.
4. **Range and Hash Partitioning**:
   - Tables are range partitioned on creation timestamp and hash partitioned on `target_id` to distribute write execution lock ranges, avoiding lock hotspots.

## Consequences
- **Unlimited Scalability**: Transitioning analyses to write-once ledger records enables parallel evaluation workers to execute without locks, scaling easily to 100M+ runs per day.
- **Minimized complexity**: Retiring snapshot aggregates and children keeps DB layouts simple.
- **Robust auditing**: Cryptographic snapshots ensure history cannot be modified undetected.
