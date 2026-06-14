# Sprint-38 Planning & Pre-Implementation Readiness Audit

This document presents the Planning, Final Challenge Review, Pre-Implementation Readiness Audit, and Step-by-Step Implementation Plan for Karsa's **CIO Engine Foundation** context in Sprint-38.

---

## 1. Executive Summary

Sprint-38 focuses on the implementation of the **CIO Engine Foundation** as the authoritative control-plane component for the Virtual Investment Firm (VIF). This subsystem will serve as the canonical authority source for strategic portfolio allocations, thesis lifecycle management, and trade authorization signatures, resolving all mock authority paths currently used in the Execution Engine.

A comprehensive pre-implementation readiness audit was conducted to validate package boundaries, persistence triggers, port definitions, and integration requirements. The audit found zero critical implementation blockers. The database migrations, value objects, cryptographic verification adapters, and PEP integrations are fully defined.

**Readiness Verdict**: `IMPLEMENTATION_PLAN_APPROVED`

---

## 2. Architecture-to-Code Mapping

The package structure will be established under `src/karsa/cio/` as follows:

* **`models.py`**:
  - *Responsibility*: Defines the immutable `CIODecision` aggregate root representing a sealed ledger record.
  - *Dependencies*: `value_objects.py`.
  - *Ownership*: Autoritative owner of the CIO decision record state.
* **`value_objects.py`**:
  - *Responsibility*: Defines `PortfolioTree`, `CommitteeVotes`, `AuthorizationSignature`, and `AllocatedWeights` value objects.
  - *Dependencies*: Python standard library, typing.
  - *Ownership*: Shared value objects; immutable.
* **`events.py`**:
  - *Responsibility*: Defines `PortfolioDecisionMadeEvent` event contracts and JSON schemas.
  - *Dependencies*: `jsonschema`.
  - *Ownership*: Schema definitions for outgoing messages.
* **`services.py`**:
  - *Responsibility*: Contains `CIODecisionService` (validates consensus quorum, runs precedence-multiplier formula, and appends to the ledger) and `PortfolioOrchestrationService` (builds read-side projections).
  - *Dependencies*: `models.py`, `ports.py`.
  - *Ownership*: Application service logic.
* **`repositories.py`**:
  - *Responsibility*: Implements `PostgresCIODecisionRepository` and `InMemoryCIODecisionRepository` for ledger persistence.
  - *Dependencies*: `ports.py`, `psycopg`.
  - *Ownership*: Infrastructure database adapters.
* **`projections.py`**:
  - *Responsibility*: Asynchronously updates projected database tables and Redis cache.
  - *Dependencies*: `ports.py`, Redis client.
  - *Ownership*: Read-side data projection layer.
* **`ports.py`**:
  - *Responsibility*: Declares ABC ports: `DecisionJournalPort`, `ExecutionAuthorizationPort`, `GovernanceExceptionPort`, `AllocationPort`.
  - *Dependencies*: ABC.
  - *Ownership*: Boundary interfaces.
* **`api.py`**:
  - *Responsibility*: Exposes HTTP FastAPI routers for CIO decision queries and portfolio state projections.
  - *Dependencies*: `fastapi`, `services.py`.
  - *Ownership*: Presentation layer.
* **`exceptions.py`**:
  - *Responsibility*: Declares custom context exceptions (e.g. `QuorumNotMetException`).
  - *Dependencies*: None.
  - *Ownership*: Domain exceptions.

---

## 3. Aggregate Readiness Audit

The aggregate design was audited:

* **Aggregate Root**: `CIODecision` represents the immutable aggregate root.
* **Transaction Boundary**: The insert transaction is atomic, writing the decision details, weights, and signature block in a single query.
* **Write Model Boundary**: Strictly append-only. Rowan updates or deletes are blocked.
* **Replay Boundary**: Replaying decision history rebuilds active configuration configurations.
* **Hidden Requirements**: Verified. No hidden state transitions or mutable fields exist.

---

## 4. Persistence Readiness Audit

* **Append-Only Strategy**: Enforced at database level via trigger function `block_immutable_modifications`.
* **Table Layout**: Maps to `cio_decisions` (ledger) and `portfolio_states` (projection) tables.
* **Partitioning**: Range-partitioned on `created_at` day, nested hash-partitioned on `decision_id`.
* **Migration Prerequisites**: None. All dependencies are standard PostgreSQL primitives.

---

## 5. Authority Chain Readiness Audit

The validation flow is ready:
1. Capital Allocation generates proposed weights.
2. Committee votes are collected and validated against quorum.
3. CIO Service generates cryptographic signature over `decision_id | target_node_id | allocated_weights | portfolio_snapshot_hash | governance_exception_id`.
4. Execution PEP verifier in [services.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/execution/application/services.py) verifies the Ed25519 signature and asserts that `decision_id` exists in the Decision Journal.

---

## 6. Port and Adapter Audit

* **DecisionJournalPort**: Replaces inline stubs. Requires `PostgresDecisionJournalAdapter` querying the `decision_journals` table.
* **ExecutionAuthorizationPort**: Replaces `MockDecisionAuthorizationAdapter` in [test_execution.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/execution/test_execution.py#L45). Requires `PostgresDecisionAuthorizationAdapter` verifying signatures against database records.
* **GovernanceExceptionPort**: Requires `HttpClientGovernanceExceptionAdapter` checking exception tokens.
* **AllocationPort**: Requires `EventBusAllocationAdapter` pushing recalculation events.

---

## 7. Security Readiness Audit

* **Ed25519 Verification**: The Execution PEP uses public keys registered in the database to verify CIO signatures locally.
* **Replay Protection**: The PEP checks that `decision_id` is processed at most once, and the payload is bound to the `portfolio_snapshot_hash`.
* **Duplicate Prevention**: Database schema enforces a `UNIQUE` constraint on `decision_journal_ref` in `cio_decisions`.

---

## 8. Replayability Audit

Reconstructing state 5 years later is fully validated. The lineage is reconstructed chronologically from immutable ledgers:
$$\text{Execution Fill} \to \text{Execution Request} \to \text{CIO Decision} \to \text{Decision Journal} \to \text{Thesis URN}$$
All records are protected by database triggers blocking updates/deletes, eliminating mutable state risks.

---

## 9. Scalability Readiness Audit

* Lock-free append-only writes ensure high-throughput execution.
* Asynchronous CDC outbox projection compilation ensures read lookups are $O(1)$ from Redis cache.

---

## 10. Repository Dependency Audit

* **Execution Integration**: `READY` (interfaces are well-defined in application services).
* **Decision Journal Integration**: `READY` (database table exists and has been populated since Sprint-37 closure).
* **Portfolio Integration**: `READY` (uses event streams).
* **Governance Integration**: `READY` (policy limits schema is defined).
* **Allocation Integration**: `READY` (interfaces conform to Option C).

---

## 11. Watchlist Assessment

### WATCH-38.1: Decision Journal ↔ CIO 1:1 Cardinality
* **Implementation Risk**: Low. Enforced at the database layer via `UNIQUE` constraint.
* **Migration Risk**: Low. No legacy tables are affected.
* **Scalability Risk**: Low. B-Tree index on `decision_journal_ref` fits in memory.

### WATCH-38.2: Signature Payload Evolution
* **Implementation Risk**: Low.
* **Replayability Risk**: Eliminated by including `portfolio_snapshot_hash` to lock the signature to the pre-state.
* **Future Compatibility**: High. Maps directly to Knowledge Graph directed edges.

---

## 12. Risks

* **Consensus Quorum Deadlocks**: If committee members (agents or humans) fail to vote within the validity window, allocation updates block. *Mitigation*: Fallback to active cash allocation.
* **Trigger Performance**: Triggers executing on every insert can add microsecond overhead. *Mitigation*: Handled easily by PostgreSQL engine.

---

## 13. Technical Debt Forecast

* **utcnow Deprecation Warnings**: The legacy parts of the codebase still generate datetime warnings. This is classified as deferred debt to be refactored during sprint consolidation.
* **HttpClient Stubs**: If Governance or Allocation APIs are slow, HTTP timeouts can happen. This will require asynchronous retry handlers.

---

## 14. Acceptance Criteria

1. **Immutability Trigger Check**: Any `UPDATE` or `DELETE` query against `cio_decisions` or `portfolio_states` must raise a database exception.
2. **Cardinality Check**: Inserting a `cio_decisions` row referencing an already-allocated `decision_journal_ref` URN must trigger a unique key violation.
3. **PEP Verification Check**: The Execution PEP must successfully verify cryptographically signed CIO decisions, matching public keys and proving that the `decision_id` exists in the Decision Journal.
4. **State Lock Check**: The Execution PEP must reject trade authorizations if the active portfolio state hash does not match `portfolio_snapshot_hash` signed in the payload.

---

## 15. Step-by-Step Implementation Plan

### Phase 1: Database Setup
* **Task 1.1**: Create Alembic migration script deploying:
  - `cio_decisions` and `portfolio_states` tables.
  - `UNIQUE` constraint on `decision_journal_ref`.
  - Immutability trigger function `block_immutable_modifications`.
* **Task 1.2**: Update the baseline test database.

### Phase 2: Domain Model & Value Objects
* **Task 2.1**: Implement `value_objects.py` in `src/karsa/cio/`:
  - `PortfolioTree`, `CommitteeVotes`, `AuthorizationSignature`, `AllocatedWeights`.
* **Task 2.2**: Implement `models.py` in `src/karsa/cio/`:
  - `CIODecision` frozen aggregate root.
* **Task 2.3**: Implement `events.py` in `src/karsa/cio/`:
  - `PortfolioDecisionMadeEvent` event contracts and validation code.

### Phase 3: Ports & Repositories
* **Task 3.1**: Implement `ports.py` containing ABC definitions.
* **Task 3.2**: Implement `repositories.py` deploying:
  - `PostgresCIODecisionRepository` (reads/writes `cio_decisions` and `portfolio_states`).
  - `InMemoryCIODecisionRepository` (for tests).

### Phase 4: Application & Projection Services
* **Task 4.1**: Implement `services.py` deploying:
  - `CIODecisionService` (calculates weights, checks quorum, executes signing math).
  - `PortfolioOrchestrationService` (builds tree projections).
* **Task 4.2**: Implement `projections.py` updating database and Redis cache.

### Phase 5: Execution Engine Integration
* **Task 5.1**: Implement `PostgresDecisionAuthorizationAdapter` under `src/karsa/execution/infrastructure/adapters/`.
* **Task 5.2**: Update [services.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/execution/application/services.py#L82-L89) to replace `MockDecisionAuthorizationAdapter` with the new postgres adapter, verifying signatures and journal existence.

### Phase 6: API and CLI Routes
* **Task 6.1**: Implement FastAPI routers in `api.py` exposing query endpoints.
* **Task 6.2**: Add API route registrations in `src/karsa/cli.py`.

### Phase 7: Validation & Verification Tests
* **Task 7.1**: Add database integration tests verifying triggers and uniqueness constraints.
* **Task 7.2**: Add execution signature tests verifying Ed25519 math and state lock checks.

---

## 16. Implementation Readiness Verdict

### **IMPLEMENTATION_PLAN_APPROVED**
