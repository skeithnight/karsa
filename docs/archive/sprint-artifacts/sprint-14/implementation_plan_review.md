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
