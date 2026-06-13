# Sprint-12 Thesis Engine Foundation - Implementation Planning Package

## 1. Executive Summary
This document serves as the formal Implementation Planning Package for the Sprint-12 Thesis Engine Foundation. The architecture is strictly frozen. This plan outlines the exact package structure, class designs, database schemas, and integration patterns required to build the Thesis domain. It explicitly mandates the usage of the existing `VersionedAggregate`, `UnitOfWork`, and `OutboxRecord` patterns established in Sprint-11.5 without deviation. 

## 2. Architecture Freeze Validation
- **Status**: ARCHITECTURE_FROZEN.
- **Constraints Checked**: No new bounded contexts, no knowledge graphs, no artifact registries.
- **Foundation Checked**: Preserves Single Aggregate UoW, OCC, Outbox, and PlatformEventEnvelope.

## 3. Package Structure
```text
src/karsa/thesis/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── model/
│   │   ├── __init__.py
│   │   ├── thesis.py
│   │   └── value_objects.py
├── application/
│   ├── __init__.py
│   ├── service/
│   │   ├── __init__.py
│   │   └── thesis_application_service.py
│   └── commands.py
├── infrastructure/
│   ├── __init__.py
│   └── storage/
│       ├── __init__.py
│       ├── thesis_mapper.py
│       └── thesis_repository.py
└── events/
    ├── __init__.py
    └── thesis_events.py
```

## 4. File Creation Plan
- `src/karsa/thesis/domain/model/thesis.py`: Contains `Thesis` aggregate.
- `src/karsa/thesis/domain/model/value_objects.py`: Contains enums and frozen dataclasses (VOs).
- `src/karsa/thesis/application/commands.py`: Contains command models.
- `src/karsa/thesis/application/service/thesis_application_service.py`: Application orchestration.
- `src/karsa/thesis/events/thesis_events.py`: Event payload definitions.
- `src/karsa/thesis/infrastructure/storage/thesis_mapper.py`: JSONB packing/unpacking.
- `src/karsa/thesis/infrastructure/storage/thesis_repository.py`: Persistence boundary.

## 5. File Modification Plan
- `src/karsa/shared/domain/identity.py`: Expand `OriginatorIdentity` to include `originator_worker_id`, `originator_model`, `originator_strategy`.

## 6. Class Design
- **`Thesis`**: Inherits `VersionedAggregate`.
- **`ThesisApplicationService`**: Injects `ThesisRepository`, `UnitOfWork`.
- **`PostgresThesisRepository`**: Injects `psycopg_pool.ConnectionPool`.

## 7. Aggregate Implementation Design
```python
class Thesis(VersionedAggregate):
    identity: ThesisIdentity
    state: ThesisState
    originator: OriginatorIdentity
    contributors: list[ThesisContributor]
    hypothesis: HypothesisStructure
    confidence: ConfidenceModel
    time_horizon: TimeHorizon
    research_lineage: list[ResearchReference]
```
Methods: `propose()`, `activate()`, `reject()`, `update_confidence()`, `invalidate()`, `realize()`. All methods must call `self.increment_version()`.

## 8. Value Object Implementation Design
All VOs will be implemented as `@dataclass(frozen=True)` to guarantee immutability.
Enums: `ThesisState`, `ContributionRole`, `ConfidenceSource`, `TimeClassification`.
`ThesisContextSnapshot` will mirror `Thesis` state but devoid of domain behavior.

## 9. Repository Design
```python
class ThesisRepository(ABC):
    @abstractmethod
    def get_by_id(self, thesis_id: ThesisIdentity) -> Thesis | None: ...
    @abstractmethod
    def save(self, thesis: Thesis) -> None: ...
```

## 10. Persistence Mapping Design
`thesis_mapper.py` will serialize `HypothesisStructure`, `ConfidenceModel`, `TimeHorizon`, `contributors`, and `research_lineage` into a single Python dictionary before persistence into the `payload` JSONB column.

## 11. Event Schema Design
`thesis_events.py` will define payloads utilizing standard types.
E.g., `ThesisProposedPayload` contains a serialized `ThesisContextSnapshot`.
`ThesisReviewedPayload` contains `thesis_id` and `ThesisReviewRecord`.

## 12. Command Model Design
```python
@dataclass
class ProposeThesisCommand:
    thesis_id: str
    originator: dict
    hypothesis: dict
    time_horizon: dict
    research_refs: list[dict]
```
Similar commands for `update_confidence`, `invalidate_thesis`, `add_contributor`, `apply_governance_decision`, and `record_review`.

## 13. Application Service Design
```python
class ThesisApplicationService:
    def __init__(self, uow: UnitOfWork, repo: ThesisRepository):
        self.uow = uow
        self.repo = repo

    def propose_thesis(self, cmd: ProposeThesisCommand):
        with self.uow:
            thesis = Thesis.create(...)
            thesis.propose()
            self.repo.save(thesis)
            event = PlatformEventEnvelope(payload=ThesisProposedPayload(...))
            self.uow.outbox_repository.save(OutboxRecord.from_envelope(event))
```

## 14. UnitOfWork Integration Design
Strict reliance on `with self.uow:`. No network calls within the block. Exiting the block triggers Postgres `COMMIT`.

## 15. Outbox Integration Design
`OutboxRecord` creation mapped directly inside the `uow` context. The dispatcher daemon developed in Sprint-11.5 handles all actual publishing.

## 16. Governance Saga Integration Design
`apply_governance_decision(cmd)` receives approval/rejection.
It loads `Thesis`, calls `thesis.activate()` or `thesis.reject()`, saves state, and stages `ThesisActivatedEvent` or `ThesisRejectedEvent`.

## 17. Database Schema Design
```sql
CREATE TABLE thesis (
    thesis_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    version INT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## 18. Sequence Flows
**Record Review Flow**:
`record_review(cmd)` -> `with self.uow:` -> `repo.get_by_id()` -> check exists -> build `ThesisReviewedPayload` -> `outbox.save()` -> commit. (Aggregate is untouched).

## 19. Validation Rules
- `ConfidenceModel.raw_confidence` must be `0.0 <= x <= 1.0`.
- Cannot call `activate()` if state is not `PROPOSED`.
- Cannot add a contributor with `AUTHOR` role (reserved for `originator`).

## 20. Error Handling Design
- Domain exceptions (`InvalidThesisStateTransitionError`).
- Infrastructure exceptions (`ConcurrencyConflictError` translates to HTTP 409).

## 21. OCC Implementation Design
`ThesisRepository.save()` translates to:
`UPDATE thesis SET payload = %s, state = %s, version = %s WHERE thesis_id = %s AND version = %s`
Throws `ConcurrencyConflictError` if `rowcount == 0`.

## 22. Testing Strategy
- Unit tests for `Thesis` aggregate state transitions.
- Unit tests for `ValueObject` validation.
- Mocked UoW tests for `ThesisApplicationService`.
- Postgres integration tests for `ThesisRepository` utilizing SQLite or Postgres Testcontainers.

## 23. Unit Test Plan
- `test_thesis_cannot_draft_from_active()`
- `test_confidence_bounds_validation()`
- `test_snapshot_generation_is_immutable()`
- `test_aggregate_version_increments_on_mutation()`

## 24. Integration Test Plan
- `test_postgres_thesis_repo_occ_failure()`
- `test_app_service_propose_saves_outbox()`
- `test_app_service_governance_saga_transitions()`

## 25. Migration Plan
Execute single DDL script to create `thesis` table. No data migration needed.

## 26. Rollback Plan
If deployment fails, schema creation is harmlessly dropped. No legacy data is corrupted as the domain is entirely isolated.

## 27. Risk Assessment
Risk: UoW lock contention if hundreds of fast-paced confidence updates hit the same thesis.
Mitigation: OCC handles conflicts cleanly. Caller implements jittered retries.

## 28. Technical Debt Assessment
The persistence layer relies on JSONB. While this solves mapping complexity, it pushes analytical querying complexity downstream to future projection engines. This debt is acceptable under current architecture frozen constraints.

## 29. Production Readiness Assessment
Schema is strictly defined, UoW provides atomic guarantees, Outbox ensures at-least-once delivery, OCC prevents race conditions. Production readiness is HIGH.

## 30. Final Implementation Verdict
**READY_FOR_IMPLEMENTATION**
