# Sprint-30 Capital Allocation Engine Foundation - Final Freeze Remediation Review

This document contains the final architecture freeze remediation review for Karsa's Capital Allocation Engine Foundation, resolving all outstanding findings (FIND-30.1 through FIND-30.12).

---

## 1. Executive Summary

This final remediation review addresses the architectural findings identified before the Sprint-30 architecture freeze. The design of the Capital Allocation Engine has been expanded to support a two-pass **Hard Gate vs Soft Multiplier** model for eligibility and scoring, a multi-tiered **Portfolio Risk Budget Model** allocating both capital and risk budgets recursively, a three-tiered **Governance Severity Model** (WARNING, SOFT_LIMIT, HARD_STOP), a clear **CIO Offline Policy** ensuring operational continuity under last approved weights, a strict **Attribution Recalculation Policy** to preserve historical replay stability, and an explicit **Exploration Floor Ownership Model**.

All domain rules are decoupled, lock-free, and conform to the Virtual Investment Firm (VIF) target architecture.

---

## 2. Findings Resolution Matrix

| Finding ID | Title | Severity | Status | Remediation Action |
| :--- | :--- | :--- | :--- | :--- |
| **FIND-30.1** | `AllocationPolicy` Aggregate Inflation | **High** | **RESOLVED** | Reclassified `AllocationPolicy` as an Immutable Write-Once Ledger Entry. |
| **FIND-30.2** | Stale Attribution Dependency | **High** | **RESOLVED** | Mandated snapshot-copying of active attribution scores inside object-store context payload. |
| **FIND-30.3** | Raw Agent Confidence Leakage | **Medium** | **RESOLVED** | Enforced Brier score discount calibration on raw confidence bounds. |
| **FIND-30.4** | Active Policy Authority | **High** | **RESOLVED** | Implemented the Governance-Validated, CIO-Signed Policy hybrid model. |
| **FIND-30.5** | Learning Signal Integration | **High** | **RESOLVED** | Designed a multi-factor Allocation Evidence Weighting Model. |
| **FIND-30.6** | Portfolio-Centric Future Compatibility | **High** | **RESOLVED** | Modeled target configurations using a polymorphous target hierarchy. |
| **FIND-30.7** | Hard Gates vs Soft Multipliers | **High** | **RESOLVED** | Designed a three-layer eligibility and scoring architecture separating hard stops from soft multipliers. |
| **FIND-30.8** | Portfolio Risk Budget Model | **High** | **RESOLVED** | Designed a covariance-constrained risk hierarchy allocating capital and risk. |
| **FIND-30.9** | Governance Severity Model | **Medium** | **RESOLVED** | Established severity classes (WARNING, SOFT_LIMIT, HARD_STOP) for compliance overrides. |
| **FIND-30.10** | CIO Offline Policy | **High** | **RESOLVED** | Selected Option B (Continue Last Approved Policy) with active Governance override. |
| **FIND-30.11** | Attribution Recalculation Policy | **Medium** | **RESOLVED** | Snapshotted historical attribution; flag variance > 10% as Reallocation Candidate. |
| **FIND-30.12** | Exploration Floor Ownership | **Medium** | **RESOLVED** | Defined explicit boundaries for defines, calculates, approves, and audits roles. |

---

## 3. Hard Gate vs Soft Multiplier Model (FIND-30.7)

To prevent capital leakages into non-compliant, failing, or uncalibrated targets, the allocation model enforces a strict separation between binary eligibility gates (Hard Gates) and mathematical scaling metrics (Soft Multipliers).

### 3.1 Hard Gate vs. Soft Multiplier Matrix

| Input Signal | Evaluation Category | Value / Target Action | Rationale |
| :--- | :--- | :--- | :--- |
| **Governance Breach** | Hard Gate | Eligibility = 0.0 (Status: Ineligible) | Compliance is non-negotiable. Breaches halt all trade activities immediately. |
| **Severe Review Failure** | Hard Gate (Score < 0.30) | Eligibility = 0.0 (Status: Ineligible) | Indicates complete process breakdown or severe operational risk. |
| **Moderate Review Failure** | Soft Multiplier (Score $\ge$ 0.30) | $0.5 + 0.5 \times \text{Review Score}$ | Linearly scales allocation size according to review quality. |
| **Extreme Confidence Calibration Failure** | Hard Gate (Brier > 0.80) | Eligibility = 0.0 (Status: Ineligible) | Defunds agents that are worse than random guessing and highly overconfident. |
| **Confidence Calibration** | Soft Multiplier (Brier $\le$ 0.80) | $1.0 - \text{Brier Score}$ | Discounts capital weight by predictive error. |
| **Active Probation** | Soft Multiplier | 0.50 scaling multiplier | Limits exposure during the probation validation window. |
| **Active Exception Override** | Soft Multiplier | 0.50 scaling multiplier | Permits temporary operations under half cap during exception. |

### 3.2 Evaluation Layers
1. **Eligibility Evaluation Layer**: The engine checks all Hard Gates. If any hard gate is triggered, the node's eligibility status is set to `INELIGIBLE` and its allocation multiplier is set to `0.0` immediately. No further scoring is done.
2. **Allocation Scoring Layer**: Evaluates only `ELIGIBLE` nodes. Applies soft multipliers (attribution, review score, Brier score calibration) to compute the target's raw scoring weight.
3. **Final Recommendation Layer**: Applies soft multiplier penalties (Probation, Exception Override), followed by diversification caps and exploration floors. Normalizes remaining weights to sum to 100% of available capital.

- **Replay Implications**: Hard gates make historical calculations highly deterministic. By separating eligibility from scoring, replay audits can immediately identify why a node was defunded (e.g. Brier threshold vs governance breach) without dissecting complex joint decay formulas.
- **Governance Implications**: Governance overrides directly act on the first evaluation pass (Eligibility Evaluation Layer), ensuring zero code path can bypass them.
- **CIO Implications**: The CIO Agent cannot bypass eligibility gates. It can only review and select alternatives among targets that successfully pass the Eligibility Evaluation Layer.

---

## 4. Portfolio Risk Budget Architecture (FIND-30.8)

The target VIF architecture requires allocating both **Capital** (USD/virtual currency limits) and **Risk** (volatility, drawdown limits, and exposure ceilings).

### 4.1 Risk Budgeting Definitions
- **Risk Budget**: Total permitted volatility (standard deviation of returns) allocated to a node.
- **Risk Capacity**: The maximum loss a target node can absorb before automatic liquidation/quarantine.
- **Drawdown Budget**: Maximum peak-to-trough drop allocated to a node (e.g., 5% max drawdown).
- **Exposure Budget**: Maximum gross/net market exposure (leverage cap) assigned to a node.

### 4.2 Hierarchy and Propagation
Risk and capital budgets propagate top-down:
```
           [Portfolio Risk Budget]
                      |
           [Strategy Risk Budget]
                      |
            [Thesis Risk Budget]
                      |
             [Worker Risk Limit]
```
At each node, the parent risk budget acts as an absolute ceiling. The sum of child risk budgets is constrained by covariance-adjusted limits:
$$\sigma_p = \sqrt{w^T \Sigma w} \le \text{Portfolio Risk Budget}$$
Where $w$ represents child allocation weights and $\Sigma$ is the historical covariance matrix. If a child's volatility profile increases, the Capital Allocation Engine dynamically scales down its capital budget to keep the parent node within its risk ceiling.

### 4.3 Ownership Matrix

| Actor / Context | Responsibility | Bounded Context Owner |
| :--- | :--- | :--- |
| **Governance Engine** | Owns risk ceilings and hard guardrail breach rules. | Governance |
| **Capital Allocation** | Calculates and distributes capital and covariance-adjusted risk budgets. | Capital Allocation |
| **CIO Agent** | Sets strategic risk targets and signs off on allocations. | CIO |

### 4.4 Event Contracts
The `AllocationAdjustmentRecommendedEvent` includes risk bounds:
```json
{
  "event_id": "evt_ca_rec_002",
  "event_type": "AllocationAdjustmentRecommendedEvent",
  "calculation_id": "calc_CA_5001",
  "adjustments": [
    {
      "target_type": "WORKER",
      "target_id": "worker_risk_02",
      "recommended_capital_ratio": "0.12",
      "recommended_risk_budget": {
        "max_volatility": "0.15",
        "drawdown_budget": "0.05",
        "exposure_limit": "1.50"
      }
    }
  ]
}
```

### 4.5 Persistence Model
Relational tables are updated to store risk budgets in a JSONB field:
```sql
ALTER TABLE allocation_records ADD COLUMN recommended_risk_budgets JSONB NOT NULL DEFAULT '{}';
```

---

## 5. Governance Severity Model (FIND-30.9)

Governance breaches are categorized into severity levels, each with distinct impacts on capital allocation and execution behavior.

### 5.1 Governance Severity Matrix

| Severity Level | Allocation Impact | CIO Behavior | Execution Behavior | Replay Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **WARNING** | None (soft warning). | Dispatch warning alert. | Normal operations. | Log warning string in context. |
| **SOFT_LIMIT** | 50% cap reduction. | Must submit exception request. | Positional limit reduced by 50%. | Apply $0.5$ scaling multiplier. |
| **HARD_STOP** | Defunded (Eligibility = 0). | Action blocked. | Positions liquidated immediately. | Self-verifies to 0.0. |

### 5.2 Event Contract Changes
The `GovernancePolicyBreachedEvent` is updated to include a `severity_level` enum field (`WARNING`, `SOFT_LIMIT`, `HARD_STOP`).

---

## 6. CIO Offline Policy Analysis (FIND-30.10)

What happens when the CIO Agent is offline/unavailable and standard workflow requires `Governance Approved + CIO Signed`?

### 6.1 Policy Option Evaluation Matrix

| Criterion | Option A: Fail Closed | Option B: Continue Last Approved (Canonical) | Option C: Emergency Gov Fallback |
| :--- | :--- | :--- | :--- |
| **Operational Risk** | High (stalls portfolio adjustments) | **Low** (portfolio remains stable) | Medium (unnecessary liquidations) |
| **Determinism** | High | **High** | Medium (depends on fallback state) |
| **Auditability** | High | **High** | Low (audit trace split) |
| **Replay Safety** | High | **High** | Medium (complex fallback logic) |
| **Availability** | Low (calculations halt) | **High** (continues execution) | High |

### 6.2 Selected Canonical Model
**Option B (Continue Last Approved Policy)** with emergency Governance overrides is selected. If the CIO agent is offline, the Capital Allocation Engine continues to run on the last fully approved and signed policy version. If Governance detects a breach or issue during this time, it triggers a `HARD_STOP` or `SOFT_LIMIT` override directly, cutting the target limits without waiting for CIO approval. This maintains system availability while preserving absolute governance authority.

---

## 7. Attribution Recalculation Policy (FIND-30.11)

When the Attribution Engine recalculates historical factors due to late evidence or trade corrections:

### 7.1 Lifecycle & Flow
1. **AttributionRecalculatedEvent**: Published by the Attribution Engine containing the recalculated path and variance.
2. **Immutability of Records**: Historical `AllocationRecord` entries remain immutable. They are never rewritten retrospectively. This preserves 100% replay determinism.
3. **Drift Evaluation**: The Capital Allocation Engine compares the recalculated attribution score against the snapshotted score in the historical payload.
4. **Reallocation Candidate**: If variance exceeds the drift threshold (e.g., > 10% drift), the target is marked as a **Reallocation Candidate**.
5. **New Run Triggered**: The allocator schedules a new calculation run (`TriggerAllocationCalc()`) to adjust *future* limits. A `ReviewAlert` is sent to the Review Engine for audit traceability.

---

## 8. Exploration Floor Ownership Model (FIND-30.12)

The 5%-20% exploration floor is a key constraint to prevent winner-take-all starvation.

### 8.1 Ownership Matrix

| Function | Governance Engine | Capital Allocation Engine | CIO Agent | Review Engine |
| :--- | :--- | :--- | :--- | :--- |
| **Defines bounds (5%-20%)** | **Yes** (Authoritative) | No | No | No |
| **Calculates ratio (default 8%)** | No | **Yes** (Authoritative) | No | No |
| **Approves changes to floor** | No | No | **Yes** (Authoritative) | No |
| **Audits floor compliance** | No | No | No | **Yes** (Authoritative) |

---

## 9. Event Contract Delta Analysis

| Event Type | Field Added / Modified | Reason |
| :--- | :--- | :--- |
| `GovernancePolicyBreachedEvent` | `severity_level` (Enum: `WARNING`, `SOFT_LIMIT`, `HARD_STOP`) | Supports multi-tiered governance constraint propagation. |
| `AllocationAdjustmentRecommendedEvent` | `recommended_risk_budget` (JSON object containing VaR, drawdown bounds) | Propagates risk targets alongside capital budgets. |
| `AttributionRecalculatedEvent` | `variance_score` (Numeric) | Allows the allocator to identify reallocation candidates. |

---

## 10. Replay Determinism Analysis

- **Source of Truth**: The `allocation_records` and `allocation_policies` relational tables.
- **Replay Source**: Immutable context payloads offloaded to the versioned object store.
- **Projection Source**: Downstream execution scorecards compiled by the Performance Engine.

Replay deterministic behavior is guaranteed under all scenarios:
- **Attribution Recalculation**: Historical calculations remain unchanged because the active attribution scores were snapshotted in the immutable context payload.
- **CIO Offline State**: Replay resolves the active policy as of that timestamp, ignoring offline states.
- **Governance Overrides**: Any override or breach active at the historical timestamp is recorded in the context payload, ensuring reproducible defunding calculations.

---

## 11. Ownership Boundary Matrix

| Bounded Context | Authoritative Ledgers | Allowed Writers | Read Accessors | Out-of-Bound Action |
| :--- | :--- | :--- | :--- | :--- |
| **Capital Allocation** | `allocation_policies`, `allocation_records` | `AllocationService` | CIO, Execution, Governance | Emits adjustments recommendations. |
| **Governance Engine** | `governance_decisions`, `exception_overrides` | `GovernanceService` | Allocation, Execution | Overrides limits directly. |
| **Attribution Engine** | `attribution_analyses` | `AttributionService` | Allocation | Emits recalculated events. |

---

## 12. Architecture Delta Analysis

| VIF Stage | Pre-Sprint-30 Baseline | Post-Sprint-30 Allocation Design | Remaining Gaps |
| :--- | :--- | :--- | :--- |
| **Capital & Risk Optimization** | Capital allocation via linear multipliers; raw return focus. | Two-pass eligibility gating, multi-factor risk budgeting, and severity overrides. | Execution engine integration of the risk budget payload (scheduled for future sprints). |

---

## 13. Documentation Update Matrix

| Target File | Modifications Made |
| :--- | :--- |
| `docs/architecture/20-capital-allocation-engine.md` | Added Hard Gate vs Soft Multiplier rules, Portfolio Risk Budget models, Governance Severity classes, and CIO Offline behavior. |
| `docs/adr/ADR-044-capital-allocation-and-evidence-weighting-model.md` | Documented risk budget structures, eligibility gating layers, and severity classes. |
| `docs/implementation/sprint-30/audit.md` | Added FIND-30.7 through FIND-30.12 and set status to REMEDIATED. |
| `docs/TRACEABILITY_MATRIX.md` | Updated Sprint-30 columns. |

---

## 14. Final Freeze Readiness Assessment

- **Single Writer Rule**: Verified. Only `AllocationService` modifies the allocation databases.
- **Governance Authority**: Verified. Governance decisions are hard stop gates overriding any CIO/model output.
- **Replay Stability**: Verified. Static snapshots of all dynamic inputs (attribution, governance overrides) are frozen in object storage.
- **Portfolio Compatibility**: Verified. Tree targets propagate limits recursively.

---

## 15. Final Verdict

**ARCHITECTURE_FROZEN**
