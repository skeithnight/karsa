# 25. Dependency and Critical-Path Audit Report

This report presents the post-Sprint-37 repository-wide architecture, dependency, and critical-path audit for the Virtual Investment Firm (VIF).

---

## 1. Executive Summary

Following the successful closure of Sprint-37 (Decision Journal Foundation), a repository-wide dependency and critical-path audit was conducted. The objective was to evaluate the integration status of implemented bounded contexts (Execution, Portfolio, and Decision Journal) and determine the next valid implementation sprint.

The audit has revealed that while individual bounded contexts are functionally complete, they currently operate in isolation:
* **Siloed Registry**: The Decision Journal persists reasoning logs and active leaves, but no downstream context (Execution, Performance, or Review) consumes these records.
* **Authority Gap**: The CIO Engine is completely missing. Pre-trade authorization signatures checked by the Execution PEP are fully simulated via mock test fixtures.
* **Mocked Outcomes**: The Performance Engine calculates Brier score outcomes using a hardcoded forecast probability of `0.8` rather than querying the Decision Journal's stated confidence value object.

To resolve the pre-trade authority gap, the **CIO Engine Foundation** must be implemented next. It is the blocking upstream dependency for all real trade authorizations. Therefore, the next valid sprint is validated as **Sprint-38: CIO Engine Foundation**.

**Final Verdict**: `ROADMAP_VALIDATED`

---

## 2. Repository Capability Inventory

The actual capabilities of the current codebase are inventory-mapped below:

* **Execution Engine** ([execution/](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/execution/)):
  - Stages orders, performs pre-trade PEP limit checks, routes trades to broker adapters, and indexes fill records in a write-once ledger.
  - *Status*: PEP validations for CIO and Governance signatures are fully stubbed.
* **Portfolio Engine** ([portfolio/](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/)):
  - Tracks holdings, exposures, and cash balances in a write-once ledger.
* **Decision Journal** ([decision_journal/](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/)):
  - Captures pre-outcome reasoning snapshots, checksum hashes, daily partitions, and active leaf correction chains.
* **Performance Engine** ([performance/](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/performance/)):
  - Calculates ex-post returns and rolling performance metrics.
  - *Status*: Stated confidence and forecast inputs are hardcoded in application services.
* **Review Engine** ([review/](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/review/)):
  - Evaluates signal convergence on local text files, disconnected from the Decision Journal database.

---

## 3. Dependency Matrix

| Source Context | Target Context | Dependency Type | Status | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Execution** | Decision Journal | Pre-trade Lookup | `STUBBED` | Validation checks that `decision_id` exists in the DB, but this check is mocked in tests. |
| **Execution** | CIO Engine | Signature Check | `MISSING` | CIO public keys and signature ledgers do not exist. Signatures are simulated in tests. |
| **Execution** | Governance Engine | Limit / Exception Check | `STUBBED` | Limit checking and exception token verifications are mocked in tests. |
| **Performance** | Decision Journal | Stated Confidence | `STUBBED` | Brier score calculation uses a hardcoded forecast probability of `0.8` instead of reading the journal. |
| **Review** | Decision Journal | Rationale Check | `MISSING` | Review engine does not query the `decision_journals` database. |
| **Post-Mortem** | Decision Journal | Upstream Context | `MISSING` | Post-Mortem engine is completely absent. |

---

## 4. Authority Chain Audit

The trade validation authority chain is simulated:
* **Signature Generation**: During order staging tests, Ed25519 key pairs are generated on-the-fly inside test fixtures to sign dummy payload blocks (`decision_id | symbol | quantity`).
* **Authority Verification**: The Execution PEP service verifier receives a signature and checks it against the public key passed to the mock adapter, validating Ed25519 math but not checking a real, registry-backed CIO public key.
* **Lineage Tracking**: The `correlation_id` represents the decision URN string, but no verification is done to assert that this URN points to a sealed database record.

---

## 5. Execution Authorization Audit

* **`DecisionAuthorizationPort`**: Implemented as `MockDecisionAuthorizationAdapter` in [test_execution.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/execution/test_execution.py#L45). (Status: `STUBBED`)
* **`GovernanceAuthorizationPort`**: Implemented as `MockGovernanceAuthorizationAdapter` in [test_execution.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/execution/test_execution.py#L55). (Status: `STUBBED`)
* **Production-Ready Paths**: None. The ports do not connect to external service routers or databases.
* **Unresolved Adapters**: No real database-backed or network-backed adapter implementations exist for these ports.

---

## 6. Decision Journal Integration Audit

* **Connection Status**: **Disconnected**. No active connection exists from the Execution Engine or Performance Engine to the Decision Journal database.
* **Verification path**:
  - The Execution PEP receives `decision_id` as `correlation_id` but does not check if it exists in the database before order checkout.
  - The Performance Engine's outcome consumer accepts `decision_id` as a string parameter without checking the ledger.

---

## 7. Performance Dependency Audit

The Performance Engine calculates ex-post metrics but mocks pre-outcome expectations:
* **Brier Score Calculation**: Housed in [EvaluationService.consume_execution_outcome](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/performance/application/service.py#L245):
  - `forecast_prob = Decimal("0.8") # Standard benchmark`
  - Brier score is computed as `(forecast_prob - actual_outcome) ** 2`.
* **Mocked Inputs**: The actual forecast confidence from the Decision Journal is mocked, bypassing ex-post calibration tests against real pre-outcome expectations.

---

## 8. Review Dependency Audit

* **Rationale Parsing**: The Review Engine parses text files via [parser.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/review/parser.py) but has no dependency on `karsa.decision_journal`.
* **Hindsight Prevention**: Hindsight checking on qualitative reasoning is absent.

---

## 9. Post-Mortem Readiness Audit

* **Viability**: **Not Viable**.
* **Missing Dependencies**:
  - **CIO Engine**: Required to trace who approved the decision and what factors were weighted.
  - **Risk Engine**: Required to trace ex-ante VaR projections.
  - **Post-Mortem Engine**: The engine itself is completely missing.

---

## 10. VIF Learning Loop Audit

We evaluate the VIF learning loop status across the 12 target stages:

| Stage | Status | Implementation % | Dependencies Satisfied? | Blocking Upstream Dependencies | Replay / Audit Readiness |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Research** | `NOT_PRESENT` | 0% | No | None | None |
| **Thesis** | `PARTIAL` | 20% | Yes | None | Standard file registry |
| **Decision Journal**| `COMPLETE` | 100% | Yes | Thesis URN | Range-partition database, Object Lock payload checks |
| **CIO** | `NOT_PRESENT` | 0% | No | Decision Journal | None |
| **Execution** | `COMPLETE` | 100% | No | CIO Engine (Signatures) | Write-once append-only ledgers |
| **Portfolio** | `COMPLETE` | 100% | Yes | Execution Fills | Holdings snapshots |
| **Performance** | `COMPLETE` | 100% | No | Decision Journal (Confidence) | Ex-post return window projections |
| **Attribution** | `PARTIAL` | 20% | Yes | Portfolio holdings | Mocked cost attribution |
| **Review** | `PARTIAL` | 20% | No | Decision Journal (Rationale) | Convergence text records |
| **Post-Mortem** | `NOT_PRESENT` | 0% | No | CIO, Risk, Performance | None |
| **Governance** | `PARTIAL` | 20% | No | Risk Engine | Policy limits exception tokens |
| **Allocation** | `NOT_PRESENT` | 0% | No | Risk Engine, Portfolio | None |

---

## 11. Replayability Assessment

* **Historical Replays**: The Decision Journal and Portfolio contexts support replay capabilities.
* **Gaps**:
  - Ex-ante risk simulations and covariance forecasts cannot be replayed since the Risk Engine is missing.
  - CIO strategic decisions and authorizations cannot be replayed since the CIO Engine does not exist.

---

## 12. Governance Assessment

The Governance Engine exists only as a set of rules and policy schemas. The Execution PEP validations enforce limit checks, but since `GovernanceAuthorizationPort` is mocked, no real policy verification is performed.

---

## 13. Critical Path Analysis

* **First Missing Mandatory Stage**: **CIO Engine** (VIF stage 13).
* **Highest Leverage Missing Context**: **CIO Engine** (unlocks the pre-trade authority signature registry, resolving the Execution PEP verification gap).
* **Largest Replayability Gap**: Replaying strategic decisions without a CIO ledger.
* **Largest Governance Gap**: Mocked limits validation at the PEP.
* **Largest Operational Gap**: Bounded contexts (Execution, Performance, Review) operate in isolation and do not read or verify entries from the Decision Journal database, meaning reasoning records are captured but not utilized for runtime validation or performance calibrations.

---

## 14. Architecture Delta Analysis

* **Data Plane**: Complete for basic transactions (Portfolio holdings and Execution fills are saved).
* **Control Plane**: Incomplete. The CIO context is missing, leaving trade authorization fully simulated.
* **Integration Plane**: Bounded contexts are siloed. Brier scores and PEP verifications use test fixtures.

---

## 15. Roadmap Validation

We evaluate three sprint options for the next phase of development:
1. **Option A: CIO Engine Foundation (Sprint-38)**:
   - *Analysis*: The CIO Engine provides the key registry and write-once decision ledger. Implementing it resolves the core authority gap in the Execution PEP validation path.
2. **Option B: Performance Evolution**:
   - *Analysis*: Upgrading Performance to PostgreSQL is useful, but it does not resolve the pre-trade authority blockers in the Execution PEP.
3. **Option C: Post-Mortem Engine Foundation**:
   - *Analysis*: Cannot be implemented since the upstream CIO and Risk data layers do not exist.

**Conclusion**: **Option A** is the only logical choice. CIO Engine Foundation is the blocking dependency for live execution validation.

---

## 16. Risks

* **Siloed Registry Risk**: Postponing integration leaves the Decision Journal as a disconnected database table, increasing the risk of interface mismatches during later sprints.
* **Key Registry Out of Sync**: Mocking key pairs in tests might lead to design assumptions that do not map to the real multi-signature key structure implemented in the CIO Engine.

---

## 17. Findings

1. **Disconnected Decision Journal**: No downstream contexts consume Decision Journal database records.
2. **Mocked Brier Score Forecasts**: Stated confidence is mocked as `0.8` inside `consume_execution_outcome`.
3. **Missing CIO Context**: The CIO Engine is absent, and all pre-trade validations use simulated Ed25519 signatures.

---

## 18. Recommended Sprint Ordering

1. **Sprint-38**: **CIO Engine Foundation** (Implement write-once CIO decision ledger and authorization signature logic).
2. **Sprint-39**: **VIF Integration and Consolidation** (Refactor Execution PEP and Performance Engines to query Decision Journal and CIO Engine registries directly, removing mocks).
3. **Sprint-40**: **Post-Mortem Engine Foundation**.
4. **Sprint-41**: **Risk Engine Foundation**.

---

## 19. Acceptance Criteria for Sprint-38

1. **CIO Key Registry**: Real Ed25519 public keys must be registered and resolved by the CIO context.
2. **Write-Once Ledger**: CIO decision records must be written once to a relational database table with immutable trigger protections.
3. **Cryptographic Signatures**: The CIO Engine must generate cryptographically verifiable Ed25519 signatures of approved decision payloads.

---

## 20. Final Verdict

### **ROADMAP_VALIDATED**
*Sprint-38: CIO Engine Foundation is the correct and necessary next sprint.*
