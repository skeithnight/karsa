# ADR-040: Decision Journal Immutable Record Model

## Status
Approved

## Date
2026-06-14

## Context
Designing a pre-outcome reasoning registry that scales to 100M+ journal entries per day requires a highly performant, concurrency-safe, and secure domain model. The design must address:
1. **Hindsight Bias Prevention**: Existing decisions must not be mutable after creation, preventing models or humans from modifying their reasoning retroactively once trading outcomes are known.
2. **Pre-Outcome Corrections**: If key metrics or assumptions are corrected before execution commences, the system must support updates without mutating the original entry.
3. **Aggregate Inflation**: Storing nested reasoning structures (context parameters, hypotheses, rationale steps) as separate child aggregates would create database layout bloat and lock contention during high-frequency writes.
4. **Replay Determinism**: Historical audits must verify that evaluations run against the exact context snapshots active at the historical timestamp.

## Decision
We implement the following immutable record model for the Decision Journal:

1. **Strict Immutability Rules**:
   - `DecisionJournal` is the sole aggregate root representing an immutable, write-once ledger entry.
   - Once appended, all attributes are strictly read-only. Database-level constraints block all `UPDATE` and `DELETE` actions. Attempts to modify properties at the application level raise a `TypeError`.
2. **Chained Lineage Tree (Option A)**:
   - Corrections are appended as new ledger entries with a `parent_decision_id` referencing the immediate predecessor. The lineage forms a Directed Acyclic Graph (DAG) tree.
   - The ledger stores a flat, immutable `root_decision_id` pointing to the origin record of the chain, facilitating fast leaf queries without recursive lookups.
3. **Shared Journal with Agent Contributions (Option 3)**:
   - Multiple agents propose decisions and corrections into a single shared, range-partitioned database table.
   - Every entry explicitly records the initiating agent's identity (`proposing_agent_id`) and a cryptographic signature (`signature`) to preserve absolute accountability.
4. **Database-Generated Monotonic Timestamps**:
   - Validation uses database transaction-generated timestamps (`created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`) rather than client clocks to eliminate clock drift vulnerabilities.
5. **Nested Value Objects**:
   - Nested parameters (`DecisionRationale`, `DecisionEvidence`, `DecisionHypothesis`, `DecisionConfidence`) are modeled as frozen value objects stored in JSONB.
6. **Object Store Offloading for Context Snapshots**:
   - To prevent database write bottlenecks and storage exhaustion from massive payloads (e.g. prompt templates, telemetry contexts, model weights), the complete `DecisionContext` snapshot is saved to an immutable, write-once object store (e.g., S3/GCS with Object Lock). The `DecisionJournal` database record stores only the SHA-256 `context_hash` and the `context_uri`.
7. **No Optimistic Concurrency Control (OCC)**:
   - Because all records are strictly write-once and append-only, row-level updates never occur. Therefore, OCC is completely eliminated, removing database locking and versioning overhead.

## Consequences
- **Absolute Hindsight Protection**: Database-enforced immutability guarantees that pre-outcome reasoning cannot be modified.
- **Traceable Correction Trail**: Corrections are fully audited through the append-only lineage tree.
- **Scalable Writes (100M+/day)**: By offloading heavy snapshots to object storage and removing SQL updates/OCC, write paths are highly parallelized and lock-free.
- **Audit Determinism**: All replay dependencies are snapshotted in the object store at creation time, ensuring complete reconstruction of pre-outcome reasoning.
