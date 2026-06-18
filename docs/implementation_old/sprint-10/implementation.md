# Sprint 10 Implementation Log

## Status
Work Package 1: COMPLETE
Work Package 2: COMPLETE
Work Package 3: COMPLETE_WITH_KNOWN_DEBT
Work Package 4: COMPLETE

## Details

### Work Package 1
- Created the core domain models for `WP-26 Risk Allocation Engine`.
- Implemented `RiskAllocation` as the aggregate root with strict invariant protection for lifecycle state transitions (`PENDING -> ACTIVE -> SUSPENDED -> TERMINATED`).
- Extracted parameters into `RiskBudget` containing `volatility_budget`, `drawdown_limit`, and `liquidity_constraint`.
- Verified `LiquidityConstraint` limits `max_adv_participation` and `max_days_to_liquidate`.
- Stripped all `exposure`, `gross`, `net`, and `leverage` concerns to enforce architectural boundaries (WP-18 ownership).
- Built scaling mathematics for `scale_volatility_budget()` which directly modifies `RiskBudget.volatility_budget` incrementally rather than changing state.
- Implemented `evaluate_drawdown()` which correctly monitors hard threshold breaches and transitions state to `SUSPENDED`.
- Achieved 100% unit test success covering valid transitions, invalid transitions, scaling mechanics, drawdown breaches, and liquidity constraint enforcement without bridging any WP-14 or WP-18 architectural gaps.

### Work Package 2
- Extended `RiskAllocation` aggregate root to encompass complete state machine logic.
- Implemented transitions: `PENDING -> ACTIVE`, `ACTIVE -> SUSPENDED`, `ACTIVE -> TERMINATED`, `SUSPENDED -> ACTIVE`, and `SUSPENDED -> TERMINATED`.
- Implemented strict invariant protection rejecting invalid transitions (e.g., `TERMINATED -> ACTIVE`, `TERMINATED -> SUSPENDED`, `TERMINATED -> TERMINATED`).
- All state transitions implemented purely inside the domain model (`allocation.py`) throwing `InvalidAllocationStateTransitionError`.
- Covered transitions extensively with unit tests.
- Proved with unit tests that `scale_volatility_budget` correctly alters `RiskBudget` values without mutating lifecycle state (`test_scale_volatility_budget_does_not_mutate_state`).
- Kept WP-26 isolated from portfolio construction, exposure calculation, and infrastructure concerns.

### Work Package 3
- Created `AllocationRepository` abstraction in the domain layer to enforce persistence ignorance.
- Created `RiskAllocationRecord` and related DTOs inside the infrastructure storage layer.
- Implemented `AllocationMapper` ensuring lossless mapping between the `RiskAllocation` domain aggregate and its persistence DTOs.
- Created `InMemoryAllocationRepository` for isolated testing.
- Created `PostgresAllocationRepository` using `psycopg` and `JSONB` to serialize `RiskBudget` structurally, aligning with WP-24.5 and WP-25's proven persistence design.
- Implemented robust `UPSERT` semantics using `ON CONFLICT (allocation_id) DO UPDATE`.
- Fully tested Mapper roundtripping and Repository contracts (`save`, `get_by_id`, `exists`, `delete`).
- *Note:* Integration tests executing physically against Postgres `TestContainers` were correctly coded but skipped dynamically at runtime due to lack of a Docker daemon in the local environment. Logged as known debt.

### Work Package 4
- Implemented `MemoryPlatformPort` abstraction in `src/karsa/allocation/application/port` to decouple WP-26 from WP-24.5 infrastructure.
- Implemented `AllocationApplicationService` handling the orchestration of creating, activating, suspending, scaling, and terminating `RiskAllocation` aggregates.
- Ensured dependency inversion by leveraging abstract ports and repositories inside the service.
- Published discrete artifacts for every lifecycle mutation: `ALLOCATION_CREATED`, `ALLOCATION_ACTIVATED`, `ALLOCATION_SUSPENDED`, `ALLOCATION_SCALED`, and `ALLOCATION_TERMINATED`.
- Tested the service completely using `InMemoryPlatformAdapter` and `InMemoryAllocationRepository`.
- Strictly avoided logic leakage (no portfolio, exposure, execution, or infrastructure transport details exist in the application layer).