# Sprint-13: Investment Workflow Implementation Plan

**Status:** APPROVED
**CIO Sign-off:** ✅
**Audit:** ✅ PASS WITH ADVISORIES (5 minor)

---

## Phase 1A: Domain Model ✅ DONE

| Task | Status | Tests |
|---|---|---|
| InvestmentDecision aggregate | ✅ | 32 |
| AnalystOutput entity | ✅ | included |
| DebateRound entity | ✅ | included |
| 8 domain events | ✅ | included |
| ConvictionScore VO | ✅ | 8 |
| AnalystScore VO | ✅ | 6 |
| DecisionMemo VO | ✅ | 7 |
| Enums + transitions | ✅ | 6 |
| Repository ABC | ✅ | 3 |
| In-memory repository | ✅ | included |

---

## Phase 1B: Advisory Remediation

| Task | Advisory | Effort |
|---|---|---|
| Fix `DecisionMemo` to raise `InvalidMemoError` instead of `ValueError` | ADV-001 | 5 min |
| Fix `DebateRound.debated_at` mutable default | ADV-002 | 5 min |
| Remove unused `AnalystType` import from aggregate | ADV-003 | 2 min |
| Remove unused imports from `analyst_output.py` | ADV-004 | 2 min |

---

## Phase 1C: Application Services

### Task 1: InvestmentDecisionService

**Purpose:** Command handler for decision lifecycle.

**Methods:**
- `propose_decision(command)` → creates InvestmentDecision, saves, publishes event
- `record_analyst_output(command)` → loads decision, records output, saves
- `record_debate(command)` → loads decision, records debate round, saves
- `create_memo(command)` → loads decision, sets memo, transitions to RISK_REVIEW
- `approve_decision(command)` → loads decision, transitions to APPROVED
- `reject_decision(command)` → loads decision, transitions to REJECTED
- `revise_decision(command)` → loads decision, transitions to REVISED

**Dependencies:**
- `InvestmentDecisionRepository` (port)
- `InvestmentDecisionOutboxRepository` (port)

**Tests:** 20+ tests covering all command paths

---

### Task 2: AnalystOrchestrationService

**Purpose:** Parallel analyst execution coordination.

**Methods:**
- `run_analysts(decision_id, ticker)` → orchestrates 5 analyst agents
- `get_analyst_status(decision_id)` → returns which analysts have completed

**Dependencies:**
- `InvestmentDecisionService`
- Analyst port interfaces (future: LLM integration)

**Tests:** 10+ tests

---

### Task 3: DebateService

**Purpose:** Bull/Bear debate coordination.

**Methods:**
- `conduct_debate(decision_id)` → runs bull/bear debate, records round
- `compute_conviction(analyst_scores)` → computes conviction from scores

**Dependencies:**
- `InvestmentDecisionService`

**Tests:** 8+ tests

---

## Phase 1D: Ports & Adapters

### Task 4: InvestmentDecisionOutboxRepository

**Purpose:** Transactional outbox for decision events.

**ABC methods:**
- `save_event(event)`
- `get_pending(limit)`
- `mark_sent(outbox_id)`
- `mark_failed(outbox_id)`
- `get_failed(limit)`

**In-memory implementation:** `InMemoryInvestmentDecisionOutboxRepository`

**Tests:** 5+ tests

---

### Task 5: Application Ports

**Purpose:** Port interfaces for application layer (Wave-9R pattern).

**Ports:**
- `InvestmentDecisionPort` (repository port)
- `InvestmentOutboxPort` (outbox port)

**Tests:** Boundary verification

---

## Phase 1E: Integration Layer

### Task 6: InvestmentWorkflowCommandFacade

**Purpose:** Public command interface for investment workflow.

**Methods:**
- `propose_decision(contract)` → CommandResult
- `record_analyst(contract)` → CommandResult
- `record_debate(contract)` → CommandResult
- `create_memo(contract)` → CommandResult
- `approve(contract)` → CommandResult
- `reject(contract)` → CommandResult

**Dependencies:**
- `InvestmentDecisionService`
- Command translators

**Tests:** 8+ tests

---

### Task 7: InvestmentWorkflowQueryFacade

**Purpose:** Public query interface for investment workflow.

**Methods:**
- `get_decision(decision_id)` → DecisionDTO
- `get_decisions_by_ticker(ticker)` → List[DecisionDTO]
- `get_decision_status(decision_id)` → StatusDTO

**Dependencies:**
- Projection repositories

**Tests:** 6+ tests

---

## Phase 1F: Projections

### Task 8: InvestmentDecisionProjection

**Purpose:** Read model for decision queries.

**Fields:**
- decision_id, ticker, state, conviction_level
- analyst_scores (dict), debate_count
- memo_summary, entry_price, exit_target
- created_at, updated_at

**Tests:** 5+ tests

---

## Phase 1G: Transport Layer

### Task 9: Investment Workflow Endpoints

**Endpoints:**
- `POST /investments/decisions` → propose decision
- `POST /investments/decisions/{id}/analysts` → record analyst
- `POST /investments/decisions/{id}/debate` → record debate
- `POST /investments/decisions/{id}/memo` → create memo
- `POST /investments/decisions/{id}/approve` → approve
- `POST /investments/decisions/{id}/reject` → reject
- `GET /investments/decisions/{id}` → get decision
- `GET /investments/decisions?ticker=BBCA` → list by ticker

**Tests:** 12+ tests

---

## Phase 1H: Final Audit

### Task 10: Architecture Compliance Audit

**Checks:**
- Import boundary verification
- Aggregate immutability
- Event frozen compliance
- Test coverage (target: 70+ new tests)
- ADR-140 compliance
- CIO sign-off on output

---

## Test Target

| Component | Current | Target |
|---|---|---|
| Domain (aggregates, VOs, events, entities) | 59 | 59 |
| Application services | 0 | 38 |
| Ports & adapters | 0 | 5 |
| Integration layer | 0 | 14 |
| Projections | 0 | 5 |
| Transport | 0 | 12 |
| **Total** | **59** | **133** |

---

## Dependency Order

```
Phase 1B: Advisory fixes (no dependencies)
    │
    ▼
Phase 1C: Application services (depends on domain)
    │
    ▼
Phase 1D: Ports & adapters (depends on services)
    │
    ▼
Phase 1E: Integration layer (depends on services + ports)
    │
    ▼
Phase 1F: Projections (depends on domain)
    │
    ▼
Phase 1G: Transport (depends on integration layer)
    │
    ▼
Phase 1H: Final audit (depends on all above)
```

---

## Sprint-13 Deliverables Summary

| Deliverable | Count | Status |
|---|---|---|
| Domain model files | 11 | ✅ Done |
| Application services | 3 | ⏳ Pending |
| Port interfaces | 2 | ⏳ Pending |
| Integration facades | 2 | ⏳ Pending |
| Projections | 1 | ⏳ Pending |
| Transport endpoints | 8 | ⏳ Pending |
| Tests | 133 | 59 done, 74 pending |
| ADR | 1 | ✅ Done |
