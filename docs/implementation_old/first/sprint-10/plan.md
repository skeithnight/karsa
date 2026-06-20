# Sprint-10 Plan: WP-26 Risk Allocation Engine

## 1. Executive Summary
Sprint-10 focuses on the implementation of the WP-26 Risk Allocation Engine. Operating strictly within the boundaries defined by ADR-010, the Allocation Engine evaluates confirmed theses and translates them into constrained risk budgets. It does not select securities, construct portfolios, calculate positions, execute trades, or manage treasury cash. The engine dynamically evaluates volatility budgets, drawdown limits, and liquidity constraints, scaling allocation solely in terms of abstract risk units.

## 2. Ownership Boundary Matrix
| Responsibility | Owner | Status |
|----------------|-------|--------|
| Thesis Lifecycle & Invalidations | WP-25 Thesis Engine | Out of Scope |
| Risk Budgeting & Constraint Math | WP-26 Allocation Engine | Core Scope |
| Risk Scaling & Re-weighting | WP-26 Allocation Engine | Core Scope |
| Exposure Bounds & Leverage | WP-18 Portfolio Engine | Forbidden |
| Asset/Security Selection | WP-18 Portfolio Engine | Forbidden |
| Treasury Cash Management | WP-22 Treasury Engine | Forbidden |
| Execution Algorithms | WP-14 Execution Engine | Forbidden |
| Artifact Immutable Storage | WP-24.5 Institutional Memory | Port Integration |

## 3. Domain Model
- **`RiskAllocation` (Aggregate Root)**: Represents an active risk budget assigned to a specific Confirmed Thesis.
- **`RiskBudget`**: Value object defining the overall abstract risk allocation bounding parameters, containing specifically:
  - `volatility_budget`
  - `drawdown_limit`
  - `liquidity_constraint`
- **`VolatilityBudget`**: Value object encapsulating annualized vol expectations and scaling multipliers.
- **`DrawdownBudget`**: Value object defining max drawdown thresholds and penalty functions.
- **`AllocationState`**: Enum tracking the lifecycle (`PENDING -> ACTIVE -> SUSPENDED -> TERMINATED`).

## 4. Allocation Lifecycle
1. **PENDING**: Risk allocation created following the `THESIS_CONFIRMED` event.
2. **ACTIVE**: Allocation operating within normal risk parameters. Risk budget scaling dynamically alters budget values, not the state.
3. **SUSPENDED**: Allocation temporarily frozen pending manual review.
4. **TERMINATED**: Allocation closed (e.g., triggered by `THESIS_INVALIDATED`).

**Activation Flow:**
`THESIS_CONFIRMED` -> `ALLOCATION_CREATED` (State: PENDING) -> `ACTIVE`

## 5. Risk Allocation Framework
WP-26 computes abstract risk units (e.g., target risk weight). These bounds strictly define the maximum permissible risk assigned to a thesis. WP-26 does not calculate or enforce gross/net exposures. The framework provides mathematical rules for continuous evaluation of these abstract risk budgets.

## 6. Volatility Budget Framework
WP-26 scales risk budgets inversely to realized volatility relative to the thesis's expected volatility budget. If realized volatility exceeds expectations, the `RiskAllocation` mathematically reduces its `volatility_budget` without altering the `ACTIVE` state.

## 7. Drawdown Control Framework
WP-26 tracks peak-to-trough drawdowns. Hard thresholds trigger an automatic transition to the `SUSPENDED` state. Soft thresholds trigger warning events and mathematical reductions in the `drawdown_budget`.

## 8. Liquidity Constraint Framework
WP-26 models liquidity limits mathematically for risk distribution. Risk allocations cannot exceed the risk-adjusted liquidity constraints specified in the institutional mandate.

## 9. Governance Integration
Transitions to `SUSPENDED` or boundary override requests trigger governance events. The engine enforces mathematically strict boundaries; manual interventions must be recorded as audit artifacts.

## 10. Thesis Engine Integration
WP-26 listens to WP-25 events asynchronously (or via abstract port queries in this phase). A `THESIS_CONFIRMED` event initiates allocation creation. A `THESIS_DEGRADED` event initiates budget scaling, while a `THESIS_INVALIDATED` event initiates transition to `TERMINATED`.

## 11. Institutional Memory Integration
WP-26 utilizes an abstract `MemoryPlatformPort` to publish all lifecycle changes, budget re-weightings, and scaling events to WP-24.5. The domain layer remains unaware of the physical HTTP transport.

## 12. Event Contracts
- `ALLOCATION_CREATED`: Triggered on creation following thesis confirmation.
- `ALLOCATION_SCALED`: Triggered on mathematical budget re-weighting.
- `ALLOCATION_SUSPENDED`: Triggered on hard limit breaches.
- `ALLOCATION_TERMINATED`: Triggered on thesis closure.

## 13. Persistence Design
- Hexagonal architecture: `AllocationRepository` interface in the domain layer.
- Infrastructure layer provides `PostgresAllocationRepository` mapped to JSONB payload documents for structural flexibility, matching the pattern established in WP-25.

## 14. Testing Strategy
- Unit tests validating constraint math (Volatility Budget, Drawdown Budget).
- State machine tests ensuring valid lifecycle transitions (`PENDING -> ACTIVE -> SUSPENDED -> TERMINATED`).
- Repository contract tests validating `save` and `get_by_id`.
- Port integration tests verifying artifact emission.

## 15. Work Package Breakdown
- **WP-1**: Domain Models & Allocation Math (Risk Budget, Volatility Budget, Drawdown Budget).
- **WP-2**: Allocation Lifecycle & State Machine implementation.
- **WP-3**: Persistence Layer (Repository, Mapper, Postgres implementation).
- **WP-4**: Application Service & Institutional Memory Port integration.

## 16. Acceptance Criteria
1. `RiskAllocation` aggregate rejects invalid state transitions.
2. Drawdown/Volatility math correctly scales down risk budget values without altering `ACTIVE` state.
3. No security selection, exposure, or portfolio logic exists in the codebase.
4. Repository persists allocations accurately without domain leakage.
5. All lifecycle transitions emit artifacts via the `MemoryPlatformPort`.

## 17. Risks
- Sizing mathematical algorithms can be computationally intensive if modeled recursively; care must be taken to keep `RiskAllocation` stateless regarding tick data.
- Handling asynchronous delays between `THESIS_INVALIDATED` and `ALLOCATION_TERMINATED` requires careful transactional or outbox design in future implementations.

## 18. Final Verdict
READY_FOR_IMPLEMENTATION