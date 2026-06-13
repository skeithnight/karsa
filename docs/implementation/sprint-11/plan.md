# Sprint-11 Plan: WP-18 Portfolio Engine

## 1. Executive Summary
Sprint-11 focuses on designing and implementing the WP-18 Portfolio Engine, a standalone bounded context responsible for transforming approved risk allocations from WP-26 into concrete portfolio construction decisions. The Portfolio Engine operates under strict architectural boundaries governed by ADR-010: it maps N abstract allocations to M portfolios, dynamically generates immutable `PortfolioTargetSnapshot`s, and logs the explicit mathematical optimization reasoning via `PortfolioDecision`s. It calculates true exposure and position accounting without assuming ownership of thesis lifecycles, execution routing, treasury cash management, or attribution workflows.

## 2. Ownership Boundary Matrix
| Responsibility | Owner | Status |
|----------------|-------|--------|
| Portfolio Construction & Targets | WP-18 Portfolio Engine | Core Scope |
| Settled Position Accounting | WP-18 Portfolio Engine | Core Scope |
| Exposure Calculations | WP-18 Portfolio Engine | Core Scope |
| Thesis Lifecycle | WP-25 Thesis Engine | Forbidden |
| Risk Budget/Allocation Math | WP-26 Allocation Engine | Forbidden |
| Treasury Cash Ledger | WP-22 Treasury Engine | Forbidden |
| Execution & Routing Lifecycle | WP-14 Execution Engine | Forbidden |
| Attribution Calculations | WP-XX Attribution Engine | Forbidden |
| Governance Decisions | WP-XX Governance Engine | Forbidden |
| Risk Overlays / Hedging | WP-27 Risk Overlay Engine | Forbidden |

## 3. Domain Model
- **`Portfolio` (Aggregate Root)**: Tracks settled N:M mapping of strategies, maintaining `Positions` and computing aggregate metrics.
- **`Position` (Entity)**: A settled, owned holding generated sequentially by execution fills.
- **`PortfolioTargetSnapshot` (Aggregate Root)**: First-class, versioned, immutable, and timestamped target allocation output defining ideal construction. Stored permanently in Institutional Memory.
- **`PortfolioDecision` (Value Object/Artifact)**: First-class immutable explanation describing *why* a snapshot was generated (includes `decision_id`, `decision_type`, `timestamp`, `reasoning`, `allocation_inputs`, `constraint_inputs`, `resulting_target_snapshot_id`).
- **`ExposureMetrics` (Value Object)**: Computations derived directly from owned `Positions` (e.g., gross exposure, net exposure).
- **`CashTarget` (Value Object)**: Strategic uninvested capital buffer desired by the portfolio.

## 4. Portfolio Lifecycle & Frameworks
### 4.1 Lifecycle States
- **INITIALIZING**: Constructing mapping matrices; awaiting external dependencies (e.g., allocations, treasury limits).
- **ACTIVE**: Passively holding positions within allowed drift bounds.
- **REBALANCING**: Evaluating allocations, exposures, and constraints to compute a new `PortfolioDecision` and immutable `PortfolioTargetSnapshot`.
- **SUSPENDED**: Halted construction logic due to hard constraint violations or manual governance intervention.
- **LIQUIDATING**: Systematically reducing positions toward 100% `CashTarget`.

### 4.2 Rebalancing Framework
Triggered by drift tolerances, schedule, or newly emitted WP-26 `RiskAllocation`s. Rebalancing is functionally pure: `Current Portfolio + Allocations + Limits -> PortfolioDecision + PortfolioTargetSnapshot`.

### 4.3 Exposure Framework
Aggregates `Position` data against `Portfolio` NAV to calculate real-time `ExposureMetrics`. Enforces mathematical bounds and actively triggers `REBALANCING` or `SUSPENDED` if gross or net leverage parameters are breached.

### 4.4 Treasury Integration
WP-18 queries an abstract `TreasuryPort` to read `BuyingPower`. It enforces optimization constraints mathematically against this cash buffer but explicitly *never* alters the master Treasury cash ledger.

### 4.5 Regime Integration
WP-18 defines a future-proof `RegimePort` consuming abstract market environments (e.g., `BULL`, `BEAR`, `RANGE`, `HIGH_VOL`, `LOW_VOL`). Portfolio optimizers may consume this as a parameter in their math, but WP-18 does not calculate the regime itself.

### 4.6 Institutional Memory Integration
Every `PortfolioTargetSnapshot` and `PortfolioDecision` is published outward via the `MemoryPlatformPort` to WP-24.5, creating a perfect, replayable audit trail of all construction rationale.

## 5. Event Contracts
### Inbound Events
- `ALLOCATION_CREATED` / `ALLOCATION_SCALED` / `ALLOCATION_TERMINATED` (From WP-26)
- `CASH_DEPOSIT` / `MARGIN_UPDATE` (From WP-22)
- `TRADE_FILLED` (From WP-14)
- `REGIME_CHANGED` (From Regime Engine)

### Outbound Events
- `PORTFOLIO_DECISION_PUBLISHED`
- `TARGET_SNAPSHOT_GENERATED`
- `TRADE_INTENT_EMITTED` (Consumable by WP-14)
- `EXPOSURE_WARNING_EMITTED`

## 6. Persistence Design
- **Architecture**: Strict Hexagonal Architecture. `PortfolioRepository` and `TargetSnapshotRepository` defined in the domain layer.
- **Implementation**: Mapped to `PostgresPortfolioRepository` using `psycopg` and `JSONB` for structural flexibility, mirroring the proven patterns from WP-25 and WP-26. No ORMs leak into the domain layer.

## 7. Scalability Analysis
- **N:M Mappings**: N `RiskAllocations` routing to M `Portfolios` creates high graph complexity. The rebalancer must evaluate updates symmetrically across all connected mandates.
- **Optimizer Load**: Rebalancing optimizers (e.g., constraint solving) are CPU intensive. The generation of `PortfolioTargetSnapshot` must be asynchronous and stateless to prevent aggregate locking.

## 8. Risks
- **Asynchronous Deadlocks**: Processing rapid stream data (e.g., consecutive `TRADE_FILLED` events) can cause contention on the `Portfolio` aggregate. Position accounting may require an Event Sourced projection in the future if volumes scale drastically.
- **Idempotency**: Execution engines may replay fills. WP-18 must handle `TRADE_FILLED` idempotently to avoid duplicating position accounting.

## 9. Work Package Breakdown
- **WP-1: Domain Models & Portfolio Construction**: Implement `Portfolio`, `Position`, `ExposureMetrics`, `CashTarget`, `PortfolioTargetSnapshot`, and `PortfolioDecision`. 
- **WP-2: Rebalancing & Exposure Engine**: Implement the stateless rebalancing math, constraint evaluation, drift tolerance, and multi-portfolio N:M mapping logic.
- **WP-3: Persistence Layer**: Implement `PortfolioRepository`, `TargetSnapshotRepository`, DTOs, Mappers, and Postgres `JSONB` storage.
- **WP-4: Application Services & Integration Ports**: Implement `TreasuryPort`, `RegimePort`, `MemoryPlatformPort`, and internal orchestrator services.

## 10. Acceptance Criteria
1. Domain creates immutable `PortfolioTargetSnapshot` objects instead of mutating active targets.
2. Domain creates first-class `PortfolioDecision` rationale artifacts capturing all optimization inputs.
3. WP-18 correctly tracks exposure and enforces bounds purely mathematically.
4. N:M mapping successfully routes a single thesis scaling event to multiple sub-portfolios.
5. `MemoryPlatformPort` successfully broadcasts all Target Snapshots and Decisions to institutional memory.
6. Zero integration with Execution routing, Treasury cash ledgers, or Hedging overlays.

## 11. Architecture Delta Analysis
Compared against the target Virtual Investment Firm architecture:
- **Alignment**: Highly aligned. The explicit extraction of `PortfolioTargetSnapshot` perfectly decouples intention from reality, allowing WP-18 to cleanly interact with Execution (WP-14) without blurring lifecycle states.
- **Boundary Corrections**: Enforcing an abstract `RegimePort` and `TreasuryPort` successfully mitigates any circular dependencies and hardcodes the dependency inversion rules set out in ADR-010.
- **Auditability**: The introduction of `PortfolioDecision` fully solves the "Why did the portfolio buy this?" question required by future Attribution and Post-Mortem engines.

## 12. Final Verdict
**READY FOR IMPLEMENTATION**