# 31. Governance Engine Foundation - Architecture Challenge Round 2

This report presents the repository-wide **Architecture Challenge Round 2** for the **Governance Engine Foundation** bounded context in Sprint-41.

---

## 1. Executive Summary

An aggressive, second-pass architecture challenge review was performed on the Sprint-41 Governance Engine design. The objective was to identify structural weaknesses, operational bottlenecks, auditability gaps, and integration issues prior to freezing the design.

The challenge has identified three critical architectural vulnerabilities:
1. **Absence of a Governance Decision Ledger**: The previous design evaluated decisions on-the-fly but did not write the outcome to an immutable database ledger, leaving no permanent audit trail.
2. **Synchronous Risk Engine Dependency**: Synchronous query mapping from Governance PDP to the Risk Engine during order checkouts introduces significant latency and availability risks.
3. **Policy Version Inflation**: Bundling signature delegation rules (`ApprovalRule`) inside the core `Policy` aggregate causes version bloating whenever organizational signature boundaries change.

To resolve these vulnerabilities, the design requires structural revisions, including the creation of a `GovernanceDecisionRecord` aggregate root, transitioning to asynchronous Risk snapshot consumption, and separating authorization delegation structures.

**Audit Verdict**: `ARCHITECTURE_REQUIRES_REVISION`

---

## 2. Governance Aggregate Boundary Re-Evaluation

The first-pass design bundled `ApprovalRule` (mapping signature requirements) inside the `Policy` aggregate. We evaluate three options:

* **Option 1: Retain Current Model (Single PolicyAggregate containing ApprovalRules)**:
  - *Analysis*: Causes policy version inflation. If the VIF adds a new CIO approver key or updates signature delegation limits, the entire compliance policy aggregate must be incremented, bloating version tables.
* **Option 2: ApprovalRule as an Independent Aggregate Root**:
  - *Analysis*: Separates signature constraints from compliance limits. However, it risks transactional inconsistency if a policy refers to a signature rule that does not exist.
* **Option 3: Separate Compliance Policies from Approval Policies (Recommended)**:
  - *Aggregate Roots*: `CompliancePolicy` (owns VaR, HHI, and leverage constraints) and `AuthorizationPolicy` (owns signature validation rules, role delegation, and approver keys).
  - *Rationale*: Compliance limits (which change based on quantitative risk models and regulations) are decoupled from organizational structure (which changes based on agent role re-assignments). This eliminates version inflation and keeps transaction boundaries clean.

---

## 3. Exception Token Domain Analysis

We evaluate how to model Exception Tokens across different scopes (Execution, Risk, Allocation, CIO):

* **Option A: Single Aggregate with Scope Value Object (Recommended)**:
  - *Analysis*: An `ExceptionToken` is a cryptographic permission slip. By using a single aggregate root with an `ExceptionScope` value object containing URN mappings (e.g., URN pointing to `RiskEvaluation` or `StagedOrder`), we maintain a unified verification interface for PEP verifiers. It maximizes scalability and simplifies auditing.
* **Option B: Separate Aggregate Types (ExecutionException, RiskException, etc.)**:
  - *Analysis*: Fragments the Exception registry. PEP engines would have to query different database tables based on override type, degrading staging throughput.
* **Option C: Polymorphic / Inheritance Model**:
  - *Analysis*: Increases database mapping complexity (Single Table Inheritance or Class Table Inheritance), introducing ORM overhead and migration difficulty.

---

## 4. Governance Decision Ledger Analysis

The previous design was missing a dedicated evaluation ledger.
* **Recommendation**: **Governance must own an immutable `GovernanceDecisionRecord` aggregate root**.
* **Rationale**:
  - *Auditability*: Captures the exact inputs and outputs of every pre-trade evaluation.
  - *Replayability*: Prevents dependency on dynamic state. If an order was allowed 5 years ago, we inspect the exact `GovernanceDecisionRecord` rather than attempting to compute past rule evaluations.
  - *Learning-Loop value*: Post-Mortem and Review engines consume this ledger to analyze why specific exceptions were granted and whether exception frequencies correlate with ex-post portfolio failures.
* **Schema**:
  - `decision_id` (PK)
  - `order_id` (correlation_id)
  - `decision_outcome` (`ALLOW`, `DENY`, `ALLOW_VIA_EXCEPTION`)
  - `policy_version_urn`
  - `exception_token_urn` (if exception override was utilized)
  - `evaluated_at` (TIMESTAMP)

---

## 5. Policy Evaluation Replayability Analysis

To reconstruct a decision five years later without hidden dependencies, the VIF requires the following audit lineage map:

```
[FillRecord]
  -> [OrderRecord / staged_at]
    -> [GovernanceDecisionRecord / evaluated_at]
      -> [CompliancePolicy / version]
      -> [ExceptionToken / token_hash]
        -> [RiskEvaluationRecord / URN] (provides the ex-ante risk state used)
```

To support this model, we must introduce the `GovernanceDecisionRecord` aggregate ledger. No calculations may run on dynamic states; all inputs are stored as frozen, immutable records referenced by URN and timestamp.

---

## 6. Governance ↔ Risk Dependency Analysis

We challenge the synchronous PDP-to-Risk query execution path:
* **Option A: Live Synchronous Lookup**: Poor availability. If the Risk Engine is offline, order execution is blocked.
* **Option B: Governance Consumes Immutable Risk Snapshots (Recommended)**:
  - *Mechanism*: Risk Engine publishes `RiskEvaluationCreatedEvent` containing calculated risk metrics. The Governance Engine listens to this event and stores the latest metrics in a local `RiskStateSnapshot` projection. When PEP limit checks run, the PDP queries this local cache.
  - *Pros*: Decouples system availability. Staging checkout latency is sub-millisecond. Replayability is secured because the exact URN of the snapshot is linked to the evaluation decision.
* **Option C: Hybrid Cache Strategy**:
  - *Mechanism*: Sync query with cache fallback.
  - *Cons*: High code complexity and inconsistent state lookups in audits.

---

## 7. Governance ↔ Allocation Ownership Matrix

We define the authoritative owners and readers for VIF target constraints:

| Capability | Authoritative Owner | Reader | Prohibited Writers |
| :--- | :--- | :--- | :--- |
| **Risk Budgets** | Governance | Capital Allocation, Risk | Capital Allocation, Risk |
| **Position Limits** | Governance | Execution PEP, Portfolio | Portfolio, Execution |
| **Sector Limits** | Governance | Execution PEP, Portfolio | Portfolio |
| **Leverage Limits** | Governance | Execution PEP, Portfolio | Portfolio |
| **Liquidity Constraints** | Governance | Capital Allocation, Risk | Capital Allocation |
| **Cash Floors** | Governance | Portfolio, CIO | Portfolio, CIO |
| **Optimization Constraints**| Capital Allocation | CIO Engine | Governance, CIO |
| **Target Weights** | Capital Allocation | CIO Engine | Governance, CIO |

*Audit Verification*: Governance defines the limit rules. Capital Allocation consumes these limits and computes target weights. CIO reviews and approves the targets. No context may overwrite rules owned by Governance.

---

## 8. Policy Proposal Workflow Analysis

Direct policy registration introduces compliance vulnerabilities.
* **Recommendation**: Implement a `PolicyProposal` aggregate root.
* **Workflow**:
  ```
  Post-Mortem Recommendation
    -> PolicyProposal (State: DRAFT)
      -> Review (State: REVIEW)
        -> Multi-signature Approval (CIO + Compliance signatures)
          -> Policy Activation (CompliancePolicy URN is registered as ACTIVE)
  ```
* **Benefits**: Restricts policy activation to cryptographically signed proposals. Provides rollback capability and supports future multi-agent workflows.

---

## 9. Registry Strategy Analysis

* **Policy Registry**: Managed as part of the `ComplianceRepository`, mapping URNs to active policy versions.
* **Exception Registry**: Managed by `ExceptionRepository` to lookup active overrides.
* **Approval Registry**: Managed by `AuthorizationRepository` to retrieve active CIO role signature blocks.
* **Scaling**: Registries utilize in-memory caches, reducing DB lookup bottlenecks.

---

## 10. Governance Authority Delegation Analysis

We define the VIF authority delegation rules:
* **Who can issue exceptions?**: **Compliance Officer Key** + **CIO Approver Key** (requires double-signature).
* **Who can approve policies?**: **CIO Committee** (requires multi-signature approval).
* **Who can activate policies?**: The **Governance Agent** (verifies signature blocks and registers the active policy URN).
* **Who can override Governance?**: **None**. No agent, including the CIO, can bypass active compliance limits without a valid Exception Token.

---

## 11. Architecture Delta Against Target VIF

* **Implemented**: Immutability bases.
* **Missing**: `GovernanceDecisionRecord` aggregate ledger, `PolicyProposal` workflow, `AuthorizationPolicy` segregation, and asynchronous Risk event consumption.
* **Partially Defined**: Exception Token scopes.
* **Future Evolution**: Multi-agent capability validations.

---

## 12. Risks

* **Audit Lineage Break**: Failing to persist the `GovernanceDecisionRecord` would prevent auditors from verifying historical override justifications.
* **Stale Risk Snapshots**: Asynchronous consumption of Risk metrics means Governance evaluates limits against the last known portfolio snapshot. Mitigated by rejecting staged orders if the portfolio snapshot timestamp is older than policy-defined pacing limits.

---

## 13. Acceptance Criteria (Required before Freeze)

1. The design must define three concrete aggregate roots: `CompliancePolicy`, `AuthorizationPolicy`, and `ExceptionToken`.
2. The design must define `GovernanceDecisionRecord` as an immutable write-once evaluation ledger.
3. The PEP verification path must run against locally cached risk states (no synchronous Risk queries).
4. The PEP must enforce Ed25519 signature checks on Exception Tokens.

---

## 14. Final Verdict

### **ARCHITECTURE_REQUIRES_REVISION**
*The design cannot be frozen. It must be revised to include the GovernanceDecisionRecord ledger, separate Compliance from Authorization policies, establish asynchronous Risk state mapping, and implement the PolicyProposal aggregate workflow.*
