# Sprint-14 Attribution Engine Foundation - Implementation Planning Package

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
