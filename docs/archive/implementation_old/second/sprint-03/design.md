# Sprint 3 Producer Foundation Redesign

## 1. First Event Challenge

**Current Proposal:** Emit `OrderFilledEvent` natively via a continuously running producer.

**Review:**

| Event | Valid First Event? | Aligns with Firm Flow? | Visible User Value? | Architectural Debt? | Classification |
|---|---|---|---|---|---|
| `OrderFilledEvent` | No | No (Bypasses research and governance) | Yes (Updates AUM) | High (Orphaned executions) | **REJECT** (as a naked origin event) |
| `MarketSnapshotCapturedEvent` | Yes | Yes (Origin of all intelligence) | No (No current UI) | None | **ACCEPT** (as true genesis event) |
| `ResearchCreatedEvent` | No | Yes (Follows Market) | No | None | **ACCEPT** (as intermediate lineage) |
| `ThesisCreatedEvent` | No | Yes (Follows Research) | No | None | **ACCEPT** (as intermediate lineage) |
| `ForecastCreatedEvent` | No | Yes (Follows Thesis) | No | None | **ACCEPT** (as intermediate lineage) |
| `ReviewCompletedEvent` | No | Yes (Follows Forecast) | No | None | **ACCEPT** (as intermediate lineage) |

**Verdict:** Generating a naked `OrderFilledEvent` violates the core domain integrity of an event-sourced investment firm. An execution cannot exist without a decision, which cannot exist without a thesis, which requires research and market data. 

---

## 2. Business Flow Analysis

**Challenge:** `OrderFilled -> Dashboard` vs `Market Snapshot -> Research -> Thesis -> Forecast -> Review -> OrderFilled -> Dashboard`

**Determination:** The full lineage flow strictly preserves domain integrity.
**Evidence:** In a CQRS/Event-Sourced system, events form an immutable ledger of truth. Injecting an `OrderFilledEvent` without its causal chain (`causation_id`, `correlation_id` linked to a thesis/decision) creates permanent technical debt—an execution that the system cannot explain or attribute. 

To satisfy the requirement of *producing visible dashboard data* without violating domain integrity, the producer must emit the **entire Genesis Lineage** in sequence. The projection worker will safely ignore the upstream events (until future sprints build their read models) but will process the terminal `OrderFilledEvent`, securely updating the dashboard while leaving a perfect, debt-free audit trail in the `event_journal`.

---

## 3. Producer Design Review

**Challenge:** Option A (Single continuous `karsa-autonomous-worker` with timer) vs Option B (One-shot `karsa-bootstrap-producer` that emits seed events and exits).

**Evaluation:**
- **Complexity:** Option B is vastly simpler. No infinite loops, no exception handling for network drops during sleep cycles.
- **Operational Risk:** Option B has near-zero risk. It runs deterministically once. Option A risks database spamming or runaway execution loops.
- **Replayability:** Option B guarantees perfect replayability. It establishes the "Genesis State" of the firm.
- **Observability:** Option B is a discrete job. It either succeeds (exit 0) or fails (exit 1).
- **Production Value:** High. It primes the system with architecturally pure data.

**Classification:**
- Option A (Timer Loop Autonomous Worker): **REJECTED**
- Option B (One-shot Bootstrap Producer): **RECOMMENDED**

---

## 4. Scheduler Review

**Evaluation:**
- APScheduler: YAGNI
- cron: YAGNI
- timer loop: YAGNI
- no scheduler: **RECOMMENDED**

**Justification:** Sprint 3 does not require recurring background activity; it requires the *validation of the event backbone*. A deterministic, one-shot bootstrap script executed during container initialization (or via manual trigger) perfectly proves the `Producer -> Journal -> Projection -> Web` flow without the immense overhead of managing stateful schedulers.

---

## 5. Projection Impact Matrix

| Event | Projection | Read Model | Dashboard Component |
|---|---|---|---|
| `MarketSnapshotCapturedEvent` | *None (Future)* | *None (Future)* | *None (Future)* |
| `ResearchCreatedEvent` | *None (Future)* | *None (Future)* | *None (Future)* |
| `ThesisCreatedEvent` | *None (Future)* | *None (Future)* | *None (Future)* |
| `ForecastCreatedEvent` | *None (Future)* | *None (Future)* | *None (Future)* |
| `ReviewCompletedEvent` | *None (Future)* | *None (Future)* | *None (Future)* |
| `OrderFilledEvent` | `PortfolioProjectionService.consume_order_filled` | `ValuationAggregate` | **CIO Dashboard (Total AUM)** |

*Note: The upstream events are intentionally included in the payload sequence to establish domain integrity, even though they currently lack projection consumers.*

---

## 6. Dashboard Value Analysis

**Ranked by priority:**

1. **Market Snapshot / Active Research / Thesis Count**
   - *Architectural Correctness:* High
   - *Implementation Effort:* High (Requires building new APIs, Postgres schemas, and UI components)
   - *User Value:* Medium
2. **Portfolio AUM / Daily P&L**
   - *Architectural Correctness:* Low (if naked), High (if part of Genesis Lineage)
   - *Implementation Effort:* Zero (Already implemented in `karsa-web` and `PortfolioValuationService`)
   - *User Value:* Very High (Core proof of platform viability)

**Conclusion:** Portfolio AUM is the only metric that proves the platform works end-to-end without requiring new UI or API development.

---

## 7. Architecture Delta Analysis

| Component | Status | Notes |
|---|---|---|
| `event_journal` | **READY** | Validated during Wave 1 Remediation |
| `projection_worker` | **READY** | Capable of consuming `OrderFilledEvent` |
| `PortfolioValuationService` | **READY** | Updates ValuationRepository |
| `karsa-web` | **READY** | Consumes `/portfolio/summary` |
| `docker-compose.yml` | **REQUIRES_CHANGE** | Add `karsa-bootstrap-producer` profile |
| `src/karsa/workers/bootstrap_producer.py` | **BLOCKING** | Script must be implemented |

---

## 8. Sprint 3 MVP Recommendation

Implement a single, one-shot executable: `karsa-bootstrap-producer`.

This script will instantiate the firm's Genesis Lineage by emitting the following sequence of events sequentially into the `PostgresEventBus`:
1. `MarketSnapshotCapturedEvent`
2. `ResearchCreatedEvent`
3. `ThesisCreatedEvent`
4. `ForecastCreatedEvent`
5. `ReviewCompletedEvent`
6. `OrderFilledEvent`

The `projection_worker` will cleanly bypass events 1-5 and process event 6. This instantly populates the `ValuationAggregate` and lights up the Karsa Web Dashboard with a non-zero Total AUM. 

This architecture introduces zero new long-running services, completely eliminates technical debt regarding event causality, and perfectly preserves future evolution paths for all domain contexts.

---

## 9. Final Verdict

**ARCHITECTURE_REQUIRES_REMEDIATION**

The original assumption (Option A: Timer-loop naked `OrderFilledEvent`) is architecturally invalid and introduces significant fake-data technical debt. The architecture is remediated by adopting Option B (Genesis Lineage Bootstrap).

### Final Sprint 3 Implementation Sequence:

1. **Create Bootstrap Script:** Implement `src/karsa/workers/bootstrap_producer.py`.
2. **Define Genesis Payload:** Hardcode the deterministic "Genesis Lineage" (Market -> Research -> Thesis -> Forecast -> Review -> OrderFilled). Ensure the `correlation_id` links the entire chain.
3. **Write to Event Bus:** Use `PostgresEventBus.publish()` to write the sequence.
4. **Update Topology:** Add `karsa-bootstrap-producer` to `docker-compose.yml` under a `profiles: ["bootstrap"]` or as an `init` container.
5. **Verify:** Run the bootstrap, confirm Karsa Web AUM updates, and confirm `event_journal` contains the full un-projected history ready for future workers.
