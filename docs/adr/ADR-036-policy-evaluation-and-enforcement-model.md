# ADR-036: Policy Evaluation and Enforcement Model

## Status
Approved

## Date
2026-06-14

## Context
Implementing policy compliance monitoring at scale (target: 100M+ evaluations per day) requires an extremely high-throughput, low-latency evaluation model. The design must address:
1. **Contention Bottlenecks**: Global state updates or inline database locks on target components (such as updating a target status during high-frequency execution evaluation) cause write bottlenecks, violation of Single Writer boundaries, and database deadlock cascades.
2. **Fail-Closed Verification**: If telemetry metrics (e.g. token counts, latency data) are missing or delayed, the engine must fail safely.
3. **Replay Determinism**: Historical replays and compliance audits must reproduce identical compliance decisions, even if policies or exceptions have since been updated or retired.
4. **Active Exception Routing**: Active overrides (exception requests) must be integrated into the evaluation pipeline without introducing execution latency.

## Decision
We implement a **Write-Once Append-Only Ledger model** instead of mutable aggregate roots for policy decisions and violations:

1. **Decoupled Architecture and Classification**:
   - **`GovernancePolicy`** and **`ExceptionRequest`** are retained as the only two **Aggregate Roots** in the context, as they have complex lifecycles and require strict transactional consistency.
   - **`PolicyDecision`** is classified as an **Immutable Ledger Entry** (not an aggregate). Every evaluation runs lock-free and appends a new, write-once ledger record, eliminating write locks and OCC contention entirely.
   - **`PolicyViolation`** is classified as an **Immutable Log Entry** (not an aggregate). Detected breaches append write-once violation records.
2. **Fail-Closed Rule**:
   - If required telemetry inputs are missing during evaluation, the `PolicyEvaluationService` automatically registers a compliance breach with `MISSING_TELEMETRY` as the reason. 
3. **Deterministic Evaluation Replays**:
   - Every policy version is stored as an immutable versioned record.
   - Replaying evaluations loads the historical policy version and verifies compliance against the inputs and cryptographic exception overrides active at the historical timestamp, ensuring replay outcomes are byte-for-byte deterministic.
4. **Timestamped Exception Overrides**:
   - Exception requests store absolute `start_time` and `end_time` values.
   - The evaluation pipeline matches current time against exception timestamps to determine if a condition override is active.
5. **Rebuildable Read Projections**:
   - Active compliance status for targets is represented as an eventually consistent read-side projection built by querying the latest ledger entries in the `PolicyDecision` table.

## Consequences
- **Unlimited Scalability**: Transitioning decisions and violations to write-once ledger records enables parallel evaluation workers to execute without locks, scaling easily to 100M+ runs per day.
- **Fail-safe operations**: The platform is protected from silent metric failures or communication delays.
- **Audit consistency**: System compliance status can be audited retrospectively years later with absolute correctness.
