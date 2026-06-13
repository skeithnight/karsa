# Sprint-11 Architecture Delta Review: WP-18 Portfolio Engine

## 1. Executive Summary
This document constitutes an aggressive independent architecture delta review of the newly implemented WP-18 Portfolio Engine (Sprint 11). The engine successfully implements the pure, stateless generation of `PortfolioTargetSnapshot` and `PortfolioDecision` aggregates. It maintains strict boundaries against Execution (WP-14), Treasury (WP-22), and Allocation (WP-26). However, a rigid audit of the implementation reveals hidden complexities surrounding temporal event consistency, dual-write anomalies across integration ports, and potential replayability weaknesses regarding historical `AllocationPortfolioMapping` state. While the structural foundation is remarkably clean, the architecture currently lacks systemic hooks for safe concurrency, decision lineage tracking, and robust outbox coordination, exposing integration risks for the future Virtual Investment Firm target architecture.

## 2. Architecture Delta Matrix
| Review Area | Status | Delta Analysis |
|-------------|--------|----------------|
| **Domain Boundaries** | Aligned | Strict isolation maintained. WP-18 computes math; it does not execute or route. |
| **Aggregate Design** | Aligned | Aggregates are pure. Mutable states exist clearly segregated from immutable snapshots. |
| **PortfolioTargetSnapshot** | Aligned | Implemented losslessly. SHA-256 hashed IDs guarantee physical determinism. |
| **PortfolioDecision** | Weakness | Dictionary structures exist but lack strict JSON schemas. Lineage to exact optimizer versions is missing. |
| **Rebalancing Engine** | Aligned | Functionally pure `Input -> Output`. Generates deterministic IDs based on target signatures. |
| **Repository Pattern** | Aligned | `InMemory` and `Postgres` variants correctly implement Hexagonal abstraction. |
| **Persistence Design** | Aligned | JSONB + UPSERT ensures structural flexibility without ORM leakage. |
| **Integration Ports** | Weakness | Ports correctly abstract dependencies, but lack idempotency/caching guarantees for volatile inputs. |
| **Determinism** | Aligned | Python `hash()` successfully eliminated. Canonical JSON serialization enforces target consistency. |
| **Replayability** | Weakness | Relying on `AllocationPort` to load allocations/mappings implicitly queries *current* state, risking temporal drift for historical replays. |
| **N:M Allocation Mapping** | Aligned | Graph logic functions correctly, routing abstract thesis budgets to localized portfolios. |
| **Future Attribution Compatibility** | Aligned | Immutability of Target vs Snapshot provides perfect mathematical tracking error boundaries. |
| **Future Governance Compatibility** | Weakness | No evaluation hooks exist before `MemoryPlatformPort` publishes the decision, making active intervention difficult. |

## 3. Critical Findings
**Challenge: Is PortfolioDecision sufficient?**
*No.* While structurally improved with dictionaries over strings, it lacks "Optimizer Version", "Engine Version", and "Dependency Context" metadata. Future Post-Mortem engines cannot explain anomalies if they do not know the exact computational binary version that generated the decision.

**Challenge: Is PortfolioTargetSnapshot truly immutable?**
*Yes.* The Python `frozenset` usage combined with SHA-256 hashing completely isolates it from mutation.

**Challenge: Is rebalancing fully deterministic?**
*Conditionally.* Given identical inputs, yes. However, inputs such as `RegimeState` or `BuyingPower` are fetched ad-hoc at execution time. If `RegimeState` changes by a millisecond during a rebalance loop, outputs will diverge. 

**Challenge: Can historical decisions be replayed exactly?**
*No.* The `PortfolioApplicationService` fetches current mappings via `AllocationPort.get_mappings_for_portfolio()`. If mappings change (e.g., an allocation is deactivated), a historical replay without a point-in-time (PIT) graph database will yield different target snapshots. Replay context is missing.

**Challenge: Can future attribution explain outcomes?**
*Yes.* The existence of `PortfolioDecision` linked mathematically to a `PortfolioTargetSnapshot` perfectly answers the "Why was this target requested?" query.

**Challenge: Can future governance block decisions safely?**
*No.* The `PortfolioApplicationService` synchronously persists the decision and immediately publishes it to the `MemoryPlatformPort`. Governance cannot inject an approval phase between generation and publication without fundamentally breaking the current Application Service flow.

## 4. Architecture Risks
- **Dual Write Anomalies**: The Application Service uses sequential logic to `self.snapshot_repo.save()` then `self.memory_port.publish()`. A crash between these steps results in orphaned local decisions unknown to Institutional Memory. Outbox pattern is urgently required.
- **Allocation Mapping Consistency**: N:M mappings are queried from an external bounded context. If the allocation weights mutate mid-rebalance, the `RebalancingEngine` risks generating targets based on torn state.
- **Stale Inputs (Treasury/Regime)**: The `BuyingPower` constraint is evaluated at $T=0$. By the time `TradeIntent` reaches Execution at $T=10$, margins may have moved. WP-18 blindly assumes static cash states.
- **Concurrency Risks**: Two rapid `ALLOCATION_SCALED` events hitting `PortfolioApplicationService` concurrently will race on the `PortfolioRepository.save()` UPSERT, potentially overwriting target sequence references. Optimistic concurrency control (OCC) or Event Sourced projections are missing on the `Portfolio` aggregate root.

## 5. Future Compatibility Analysis
- **Performance/Attribution Engine**: Highly Compatible. The hard decoupling of Intended Targets vs Settled Positions creates a perfect analytical gap for slippage evaluation.
- **Capital Allocation Engine**: Compatible. N:M mappings easily propagate down.
- **Worker Ranking Engine**: Compatible. Worker decisions can be mapped directly to `PortfolioDecision` hashes.
- **Governance Engine**: **Incompatible**. The Application service blindly persists and executes. It requires an interceptor hook or a PENDING state for snapshots awaiting manual/systemic sign-off.
- **Post-Mortem Engine**: Partially Compatible. Decisions are logged, but lack environmental lineage (software versioning, point-in-time mapping state).

## 6. Missing Concepts
1. **Decision Lineage Fingerprints**: `PortfolioDecision` must include `optimizer_version`, `model_version`, and `git_hash` to debug mathematically complex constraint failures.
2. **Point-In-Time (PIT) Context**: Replayability fails without knowing what the Allocation graph looked like at the exact millisecond of the decision.
3. **Evaluation Hooks / Interceptors**: Governance needs a systemic injection point between `RebalancingEngine` output and `PortfolioTargetSnapshot` execution/publishing.
4. **Optimistic Concurrency Tokens**: The `Portfolio` aggregate requires a `version` field mapped to Postgres `ON CONFLICT` to reject stale updates.

## 7. Refactor Candidates (DO NOT IMPLEMENT)
1. **Outbox Pattern Introduction**: Refactor Application Service to wrap repository saves and Outbox emissions in a single Postgres transaction block.
2. **Aggregate Versioning**: Introduce `version: int` to `Portfolio` to enable OCC.
3. **Temporal Ports**: Refactor `AllocationPort`, `TreasuryPort`, and `RegimePort` to accept an explicit `timestamp` or `context_id` to guarantee PIT retrieval.
4. **Governance State Machine**: Introduce `PENDING_GOVERNANCE` state to `PortfolioTargetSnapshot`.

## 8. Priority Ranking
- **CRITICAL**: Dual-Write Anomalies (MemoryPlatformPort vs Repository).
- **CRITICAL**: Missing Optimistic Concurrency Control on `Portfolio`.
- **HIGH**: Missing Temporal/PIT context in Integration Ports.
- **HIGH**: Missing Evaluation/Interceptor hooks for Governance.
- **MEDIUM**: Lack of Decision Lineage Fingerprints.
- **LOW**: Dictionary Schema enforcement on PortfolioDecision.

## 9. Final Verdict
**APPROVED_WITH_REVISIONS**

**Rationale**: The domain math, boundary isolation, and determinism fixes (SHA-256) are fundamentally sound and pass all target specifications. The implementation serves as a highly robust v1 Portfolio Engine. However, the lack of Outbox coordination, optimistic concurrency, and point-in-time reproducibility exposes it to failure in high-volume, multi-agent distributed architectures. It is cleared to proceed, but the noted Refactor Candidates must be addressed before physical capital execution is enabled.
