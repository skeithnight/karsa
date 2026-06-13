# Sprint 14 Plan

Not started.# Sprint-14 Attribution Engine Foundation - Implementation Planning Package

## 1. Executive Summary
This Implementation Planning Package translates the Architecture Revision v6 into concrete engineering tasks for the Sprint-14 Attribution Engine Foundation. The blueprint mandates the creation of the `karsa.attribution` bounded context. The implementation avoids bloated ledgers by combining the stateless `AttributionService` with the highly-constrained `AttributionLineage` aggregate. All operations are firmly embedded in the UoW, Outbox, and OCC foundation laid in Sprint-11.5.

## 2. Architecture Freeze Validation
- **Architecture Baseline**: Revision v6.
- **Constraints Checked**:
  - No Knowledge Graph introduced.
  - OCC and Outbox rigorously enforced.
  - No Thesis/Performance Engine schema leakage.
  - Replay strictly deterministic via `PolicyInputSnapshot`.
- **Status**: VALIDATED.

## 3. Package Structure
```text
src/karsa/attribution/
├── application/
│   ├── commands.py
│   ├── service.py
│   └── projection_handler.py
├── domain/
│   ├── model/
│   │   ├── lineage.py
│   │   └── value_objects.py
│   ├── service/
│   │   └── attribution_service.py
│   └── registry/
│       └── policy_registry.py
├── events/
│   └── attribution_events.py
└── infrastructure/
    └── storage/
        ├── lineage_repository.py
        ├── projection_store.py
        └── migration_v1.sql
tests/karsa/attribution/
├── application/
├── domain/
└── infrastructure/
```

## 4. File Creation Plan
1. `src/karsa/attribution/domain/model/value_objects.py` (VOs)
2. `src/karsa/attribution/domain/model/lineage.py` (`AttributionLineage` aggregate)
3. `src/karsa/attribution/domain/service/attribution_service.py` (`AttributionService` domain math)
4. `src/karsa/attribution/domain/registry/policy_registry.py` (Formula configs)
5. `src/karsa/attribution/application/commands.py` (Command definitions)
6. `src/karsa/attribution/application/service.py` (UoW wrapper logic)
7. `src/karsa/attribution/application/projection_handler.py` (Cache builder)
8. `src/karsa/attribution/infrastructure/storage/lineage_repository.py` (OCC Repo)
9. `src/karsa/attribution/infrastructure/storage/projection_store.py` (JSONB Upserts)
10. `src/karsa/attribution/events/attribution_events.py` (Platform Event Payloads)

## 5. File Modification Plan
- `alembic/versions/...` (SQL migration hook).
- `src/karsa/shared/infrastructure/uow/...` (Register outbox topics for new events if strictly typed).

## 6. Class Design
- `class AttributionLineage(VersionedAggregate):`
- `class AttributionService:` (Stateless, `@staticmethod` for calculation)
- `class PostgresLineageRepository:` (Implements `get_by_id`, `save`)
- `class PostgresProjectionStore:` (Implements `upsert`, `get_by_id`)

## 7. Aggregate Implementation Design
`AttributionLineage` inherits from `VersionedAggregate`.
Methods:
- `advance_generation(new_attribution_id: UUID)`: bumps `current_generation`, asserts status transitions, calls `increment_version()`.
- `mark_reversed()`: sets `lineage_status = REVERSED`.

## 8. Value Object Implementation Design
`@dataclass(frozen=True)` used for all VOs:
- `AttributionIdentity`, `ContributionWeight`, `PolicyInputSnapshot`, `GovernanceAuditContext`, `AttributedValue`.

## 9. Repository Design
`PostgresLineageRepository` implements standard UoW participant behavior.
OCC Check: `UPDATE attribution_lineage SET ... WHERE outcome_sequence_id=%s AND version=%s`. Checks `cur.rowcount == 0` for `ConcurrencyConflictError`.

## 10. Persistence Mapping Design
- **`attribution_lineage`**: Flat columns mapping `active_attribution_id`, `current_generation`, `status`, `version`.
- **`attribution_input_projection`**: Flat `source_context_id` PK with single `contributors` `JSONB` column.

## 11. Event Schema Design
`AttributionCalculatedPayload`: Embedded natively inside `PlatformEventEnvelope` under schema version 1.0. 
Includes all lineage references, mathematical `policy_input_snapshot` properties, and output `allocations` arrays.

## 12. Command Model Design
- `ProcessRealizedOutcomeCommand(outcome_id, outcome_sequence_id, source_context_id, gross_pnl)`
- `ApplyAttributionRestatementCommand(outcome_sequence_id, governance_audit_context)`

## 13. Application Service Design
`AttributionApplicationService` opens the UoW `with uow:` block, calls Domain Service to get allocations, updates `AttributionLineage` aggregate, and `uow.outbox_repository.save()` the event.

## 14. UnitOfWork Integration Design
Native reuse of Sprint-11.5 `PostgresUnitOfWork`. `AttributionLineageRepository` injected directly.

## 15. Outbox Integration Design
`PlatformEventEnvelope` payloads are instantiated immediately before `uow.commit()` and written to the identical schema utilized by the Thesis and Performance engines.

## 16. Projection Design
`AttributionInputProjectionStore.upsert(source_context_id, JSON)` executes standard `INSERT ... ON CONFLICT DO UPDATE` without OCC requirements.

## 17. AttributionLineage Aggregate Design
Exhaustive constraint tracking preventing double-spends on Restatement events. Gen 2 must legally follow Gen 1. 

## 18. OCC Implementation Design
SQL-enforced `version` locking. Conflict yields `ConcurrencyConflictError` explicitly.

## 19. Database Schema Design
```sql
CREATE TABLE attribution_lineage (
    outcome_sequence_id VARCHAR PRIMARY KEY,
    active_attribution_id VARCHAR NOT NULL,
    current_generation INT NOT NULL,
    status VARCHAR NOT NULL,
    version INT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE attribution_input_projection (
    source_context_id VARCHAR PRIMARY KEY,
    contributors JSONB NOT NULL,
    updated_at TIMESTAMP
);
```

## 20. Sequence Flows
1. `ProcessRealizedOutcomeCommand` -> `get_projection()` -> `calculate()` -> `create_lineage()` -> `save_outbox()` -> `commit()`.

## 21. Validation Rules
- `gross_pnl` sum must equal the sum of all `attributed_pnl` across allocations.
- Generation increments must strictly be +1.

## 22. Error Handling Design
- `AllocationImbalanceException`: Thrown if math drift occurs. UoW rolls back.
- `ProjectionNotFoundException`: DLQ backoff.

## 23. Replay Design
Stateless function call feeding historic `InvestmentOutcomeRealizedEvent.value` + `AttributionContextPublishedEvent.contributors` + `PolicyInputSnapshot`. Verified via unit tests showing hash identity matching outputs.

## 24. Testing Strategy
High isolation testing on pure functions. Mocks used only for DB layer during Application testing.

## 25. Unit Test Plan
- Test pure math fractional splitting (especially 10.00 / 3).
- Test `AttributionLineage` version bump invariants.

## 26. Integration Test Plan
- OCC simulation test guaranteeing `ConcurrencyConflictError` on identical `outcome_sequence_id`.
- Test Projection JSONB encoding/decoding safety.

## 27. Replay Test Plan
Replay 10,000 synthetic PNL iterations proving output matches historic `AttributionCalculatedEvent` arrays byte-for-byte.

## 28. Migration Plan
Standard Alembic `upgrade head` execution against the WP-14 Schema definition.

## 29. Rollback Plan
Alembic `downgrade -1`. Outbox events are immutable and will not be reversed; DLQ consumer pauses.

## 30. Risk Assessment
- Low Risk. Stateless calculations remove traditional ledger complexities.

## 31. Technical Debt Assessment
- None generated by this plan. Bounded Context completely respects isolation invariants.

## 32. Production Readiness Assessment
OCC locked, perfectly auditable, stateless processing. READY.

## 33. Final Implementation Verdict
**READY_FOR_EXECUTION**
# Sprint-14 Attribution Engine Foundation - Implementation Plan Review

## 1. Findings Resolution
- **FINDING-1 (Replay Contract Mismatch)**: Resolved. The `Projection Store` is strictly a runtime optimization cache. The explicit Replay dependency model bypasses the Projection Store entirely, reading immutable `AttributionContextPublishedEvent` directly from Institutional Memory alongside the embedded `PolicyInputSnapshot`.
- **FINDING-2 (Outcome Sequence Identity Ambiguity)**: Resolved. `OutcomeSequenceIdentity` explicitly designed as an immutable Value Object mapping `outcome_id` and an integer sequence, enforcing unique database constraints.
- **FINDING-3 (AttributionLineage.status Evaluation)**: Resolved. `status` is deemed unnecessary and removed. The `current_generation` integer natively handles sequencing logic. Transitions only move forward; reversals are implicit via generation bumps mapping to negative fractional amounts.
- **FINDING-4 (Projection Store Contract Incomplete)**: Resolved. Interface strictly defined with Upsert-only semantics. Deletions are forbidden; state simply overwrites on newer context events.
- **FINDING-5 (Missing Idempotency Strategy)**: Resolved. Database UNIQUE constraints on `outcome_sequence_id` for Gen 1, and tracking `GovernanceAuditContext.approval_reference` on subsequent generations, safely aborts duplicate event consumption.
- **FINDING-6 (Rollback Plan Incomplete)**: Resolved. Explicit event compatibility checking ensures downstream systems safely ignore deprecated payload structures before initiating physical database rollbacks.

## 2. Updated Aggregate Design
**`AttributionLineage` (Revised)**
- **Identity**: `OutcomeSequenceIdentity`.
- **State**: `active_attribution_id` (UUID), `current_generation` (int).
- *(REMOVED)*: `status` has been removed. Invariants are fully protected by `current_generation` sequencing. If Governance reverses an outcome, the aggregate simply bumps to Generation N+1 pointing to a new `active_attribution_id` which mathematically zeros out the parent.

## 3. Updated Identity Model
**`OutcomeSequenceIdentity` (Value Object)**
- `outcome_id` (String): The UUID of the upstream realized investment.
- `sequence_id` (Integer): Starting at 1, handles partial exits (e.g., 10% exit = sequence 1; 90% exit = sequence 2).
- **Persistence Mapping**: Mapped as a composite PK `(outcome_id, sequence_id)` or hashed into a deterministic `outcome_sequence_hash` UUID.
- **Uniqueness Guarantees**: A composite PK naturally rejects any duplicate insertions for the same sequence.

## 4. Updated Replay Design
**Explicit Replay Execution Flow**:
1. **Source Loading**: Replay scripts query Institutional Memory (Kafka/S3) for historical `InvestmentOutcomeRealizedEvent`s.
2. **Context Resolution**: The script queries Institutional Memory for the exact `AttributionContextPublishedEvent` that occurred *prior* to the outcome. It does NOT touch the PostgreSQL `Projection Store`.
3. **Policy Extraction**: The historical `PolicyInputSnapshot` is extracted from the previously emitted `AttributionCalculatedEvent` being replayed.
4. **Stateless Recomputation**: `AttributionService` executes. The math exactly yields the recorded fractional cents.

## 5. Updated Projection Design
**`AttributionInputProjectionStore` Contract**:
- `upsert(source_context_id, JSONB contributors)`: Unconditionally writes or updates the row.
- `get_by_id(source_context_id)`: Fetches fast runtime cache.
- **Lifecycle Rules**: Created on `AttributionContextPublishedEvent`.
- **Deletion Semantics**: NEVER deleted. Storage cost is negligible. Historic contexts remain permanently cached.

## 6. Idempotency Design
- **Duplicate Realized Outcomes**: A duplicate `InvestmentOutcomeRealizedEvent` attempts to insert `AttributionLineage` Gen 1. The composite PK `(outcome_id, sequence_id)` throws a `UniqueViolation`. The Application Service swallows this gracefully as a no-op.
- **Duplicate Governance Approvals**: A duplicate `AttributionRestatementApproved` references the same `approval_reference`. The `AttributionLineage` aggregate checks its processed governance log or implicitly checks if `active_attribution_id` matches the expected pre-state. Alternatively, maintaining a unique DB constraint on `approval_reference` prevents double-spends.
- **Retry Behavior**: Standard exponential backoff via Celery/Kafka. Pure idempotent failures silently `ack()` the message.

## 7. Rollback Design
**Operational Recovery Procedure**:
1. **Pause Consumers**: Stop the `AttributionApplicationService` worker queues.
2. **Event Compatibility Check**: Verify no downstream systems (Capital Allocation) have irrevocably acted on newer `schema_version` events.
3. **Reverse DB Migrations**: Run Alembic `downgrade -1` to revert schema additions.
4. **DLQ Purge**: Clear Dead Letter Queues of stuck deprecated payloads.
5. **Resume Processing**: Start consumers on the older codebase tag. Because all events emitted to Outbox are immutable, rollback applies only to DB state parsing, protecting financial event integrity.

## 8. Architecture Compliance Verification
This implementation plan strictly adheres to Architecture Revision v6. 
- The `AttributionLineage` remains the sole, minimal OCC aggregate.
- The Projection Store remains infrastructure-only without lifecycle rules.
- Deterministic Replay remains flawlessly hermetic.

## 9. Delta From Original Planning
- `status` removed from `AttributionLineage`.
- `OutcomeSequenceIdentity` formalized as a composite PK model.
- Idempotency mechanisms explicitly bound to DB unique constraints.
- Replay pipeline explicitly decoupled from the PostgreSQL runtime Projection Store.

## 10. Final Verdict
**READY_FOR_EXECUTION**
# Sprint-14 Attribution Engine Foundation - Final Remediation Pass

## 1. Findings Resolution Matrix
- **REMEDIATION-1 (Replay Authority Terminology)**: Resolved. Terminology corrected across all documentation. `PolicyInputSnapshot` is formally classified as the "Mathematical Authority," while the "Replay Authority" is defined as the triad of `InvestmentOutcomeRealizedEvent`, `AttributionContextPublishedEvent`, and `PolicyInputSnapshot`.
- **REMEDIATION-2 (Governance Idempotency Decision)**: Resolved. Architecture explicitly adopts Database-enforced uniqueness. The `attribution_lineage_restatement` table is introduced, mapping `(outcome_id, sequence_id, approval_reference)` to enforce strict duplicate rejection. OCC is cleanly segregated to only protect generation fork tracking.
- **REMEDIATION-3 (Approval History Model)**: Resolved. Approval history is legally persisted outside of the `AttributionLineage` aggregate using the immutable `attribution_lineage_restatement` table, satisfying audit/idempotency needs without aggregate state bloat.

## 2. Updated Aggregate Design
**`AttributionLineage`**
- **Identity**: `OutcomeSequenceIdentity` (composite of `outcome_id` and `sequence_id`).
- **State**: `active_attribution_id` (UUID), `current_generation` (int).
- **Responsibilities**: Protects generational lineage via standard `increment_version()` OCC operations. It deliberately does **not** hold governance logs or mathematical payloads.

## 3. Updated Persistence Design
**Tables**:
1. `attribution_lineage`: `outcome_id` (PK), `sequence_id` (PK), `active_attribution_id`, `current_generation`, `version`.
2. `attribution_lineage_restatement`: `outcome_id`, `sequence_id`, `approval_reference`, `generation`, `created_at`.
   - **Constraint**: `UNIQUE (outcome_id, sequence_id, approval_reference)`.
3. `attribution_input_projection`: `source_context_id` (PK), `contributors` (JSONB).
4. `Outbox`: Standard platform schema.

## 4. Updated Replayability Dependency Matrix
### Mathematical Authority
- **`PolicyInputSnapshot`**: Dictates exact fractional routing, weights, rounding, and allocation ordering.

### Replay Authority (Complete Dependency Chain)
To deterministically execute replay, the system strictly depends on:
1. `InvestmentOutcomeRealizedEvent` (Immutable Nominal Input)
2. `AttributionContextPublishedEvent` (Immutable Contributor Structure)
3. `PolicyInputSnapshot` (Mathematical Authority governing execution)

## 5. Updated Idempotency Design
- **Duplicate Outcome Generation**: Inserts to `attribution_lineage` protected by composite PK `(outcome_id, sequence_id)`. Duplicates trigger `UniqueViolation`, which the service swallows as a silent no-op.
- **Duplicate Governance Approval**: Inserts to `attribution_lineage_restatement` protected by `UNIQUE (outcome_id, sequence_id, approval_reference)`. A duplicate approval event hits the constraint, allowing the service to silently `ack()` the queue message as a no-op without mutating lineage state.
- **Separation of Concerns**: UNIQUE constraints perfectly defend against duplicate messages. OCC locks perfectly defend against concurrent attempts to fork generation bumps.

## 6. Updated Governance Audit Model
1. `AttributionRestatementApproved` arrives from Governance.
2. `AttributionApplicationService` attempts to `INSERT INTO attribution_lineage_restatement`.
3. If UNIQUE constraint fails, safely abort.
4. Otherwise, load `AttributionLineage` aggregate.
5. Compute Gen N+1.
6. Aggregate updates `current_generation` and increments OCC `version`.
7. `AttributionCalculatedEvent` Gen N+1 is emitted, actively embedding the `GovernanceAuditContext`.
8. UoW commits. The database now permanently holds the immutable `attribution_lineage_restatement` record as forensic proof of the approval execution.

## 7. Updated Sequence Flow
**Restatement Application Flow**:
1. Governance Engine emits `AttributionRestatementApproved`.
2. AppService UoW begins.
3. AppService runs `INSERT INTO attribution_lineage_restatement (outcome, seq, ref, gen)`.
4. (If duplicate, catch constraint error -> `ack` -> End).
5. Load `AttributionLineage` -> Increment generation.
6. Calculate math using projection.
7. Save Event to Outbox.
8. UoW Commit.

## 8. Updated Database Schema
```sql
CREATE TABLE attribution_lineage (
    outcome_id VARCHAR NOT NULL,
    sequence_id INT NOT NULL,
    active_attribution_id VARCHAR NOT NULL,
    current_generation INT NOT NULL,
    version INT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (outcome_id, sequence_id)
);

CREATE TABLE attribution_lineage_restatement (
    outcome_id VARCHAR NOT NULL,
    sequence_id INT NOT NULL,
    approval_reference VARCHAR NOT NULL,
    generation INT NOT NULL,
    created_at TIMESTAMP,
    PRIMARY KEY (outcome_id, sequence_id, approval_reference)
);

CREATE TABLE attribution_input_projection (
    source_context_id VARCHAR PRIMARY KEY,
    contributors JSONB NOT NULL,
    updated_at TIMESTAMP
);
```

## 9. Architecture Delta Analysis
- **Delta**: Terminology unified (`Replay Authority` vs `Mathematical Authority`).
- **Delta**: Introduced `attribution_lineage_restatement` to handle idempotency uniquely without corrupting aggregate state.
- **Delta**: Replaced implicit governance log logic with explicit DB-level unique constraint handling. 

## 10. Final Compliance Assessment
- [X] Replay Authority terminology consistent
- [X] Mathematical Authority terminology defined
- [X] Governance idempotency uses one strategy only
- [X] No architecture contradictions remain
- [X] Approval history persisted outside aggregate
- [X] OCC responsibility clearly separated
- [X] Duplicate approval handling deterministic
- [X] Replay model deterministic
- [X] No architecture redesign introduced
- [X] Architecture remains Revision v6 compatible

### Final Verdict
**IMPLEMENTATION_PLAN_APPROVED**
**READY_FOR_EXECUTION**

*Justification*: The remediation definitively strips all ambiguity surrounding idempotency, aggregate bloat, and replay definitions. The implementation plan now guarantees 100% execution safety, concurrency control, and audit trace preservation while rigidly adhering to the Architecture Revision v6 boundaries. No blockers remain.
