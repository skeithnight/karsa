# 65. Karsa IDX Research Platform - Round 8 Freeze Gate Review

**Status:** FREEZE_GATE_FAILED

---

## 1. Executive Summary

This document serves as the final, aggressive Freeze Gate Review for the Karsa IDX Research Platform. The architecture was presumed ready for freeze, but subjecting it to structural stress tests revealed two hidden, critical flaws. 

First, `StockProjection` was discovered to be a secondary "God Projection," heavily coupled across six distinct event streams, risking severe operational fragility. Second, the `Discovery Engine` lacked explicit governance over its anomaly thresholds, leaving a loophole where it could easily devolve into an uncontrolled Signal Engine. 

Because these boundaries require immediate structural patching and new ADR formulations, the architecture cannot proceed to implementation. The freeze gate has been rejected.

---

## 2. Ownership Boundary Matrix

| Domain / Subsystem | Current Assigned Owner | Stress Test Status |
|---|---|---|
| **Discovery Thresholds** | Discovery Engine (Implicit) | **FLAWED**. Must move to Governance Engine. |
| **Stock UI Schema** | Read Model Platform | Validated. |
| **Probability & Returns**| Forecast Engine | Validated. Resilient to regime shifts. |
| **Immutable Facts** | Evidence Registry | Validated. Cryptographically secure. |
| **Actionable Hypothesis**| Thesis Engine | Validated. Isolated from raw evidence. |

---

## 3. Projection Boundary Analysis (Challenge Area 1)

**Challenge:** Does `StockProjection` become a new God Projection?
**Audit:** Yes. It subscribes to Market Structure, Research, Forecast, Thesis, Decisions, Attribution, and Risks. It suffers from the exact same fan-in coupling risk as the previous `InvestmentIntelligenceProjection`. A minor update to a risk factor forces a complete rebuild of the stock's fundamental and market structure aggregations.
**Evaluation:** Option B is mandatory. We must split `StockProjection` into:
1.  `StockOverviewProjection`: Owns Market Structure, Foreign Flow, Fundamentals. (Low/Medium volatility).
2.  `StockResearchProjection`: Owns Analyst Consensus, Thesis, Forecast, Risks. (High volatility, workflow-driven).
**Final Verdict:** **FLAWED**. Requires new ADR to decompose `StockProjection`.

---

## 4. Discovery Governance Analysis (Challenge Area 2)

**Challenge:** Who owns the thresholds for the `OpportunityIdentifiedEvent`?
**Audit:** If the `Discovery Engine` owns its own thresholds, analysts can silently tweak the parameters (e.g., lower relative strength requirements) until the engine begins emitting what are effectively Buy/Sell recommendations, bypassing formal VIF oversight.
**Evaluation:** Option B. The `Governance Engine` must own `DiscoveryPolicy` aggregates. The `Discovery Engine` merely executes the policy constraints defined by the Chief Risk Officer (CRO) or Governance Committee.
**Failure Scenarios Prevented:** Rogue analysts tuning discovery bots into automated trading signal generators.
**Final Verdict:** **FLAWED**. Requires new ADR to formally assign `DiscoveryPolicy` to the `Governance Engine`.

---

## 5. Forecast Boundary Analysis (Challenge Area 3)

**Challenge:** Should Forecast remain a separate bounded context?
**Audit:** If Forecast merges into Thesis (Option B), a regime shift (e.g., from Bull Expansion to Bear Capitulation) would necessitate invalidating the entire Thesis just to lower the expected return from 15% to 5%, even if the core fundamental hypothesis (e.g., expanding CASA share) remains 100% valid.
**Evaluation:** Option A. Forecast must remain an independent context with a 1:N relationship to Thesis. It allows probability and returns to float dynamically against the `RegimeSnapshot` without destroying the foundational `ThesisVersion`.
**Final Verdict:** **VALIDATED**. Forecast remains a separate Bounded Context.

---

## 6. Read Model Platform Analysis (Challenge Area 4)

**Challenge:** Does infrastructure own business read-schemas?
**Audit:** The `Projection Worker` is merely a Kafka/PostgreSQL execution container. It possesses zero domain logic. The `Read Model Platform` explicitly owns the schemas, UI query contracts, and rebuild governance.
**Contract Analysis:** The UI negotiates strictly with the `Read Model Platform` API. 
**Recommendation:** Ensure repository directory structures clearly separate `infrastructure/workers/` from `application/read_model_platform/`.
**Final Verdict:** **VALIDATED**.

---

## 7. Event Contract Analysis

*   `DiscoveryPolicyUpdatedEvent`: (New) Emitted by Governance Engine. Consumed by Discovery Engine.
*   `OpportunityIdentifiedEvent`: (Updated) Must embed `policy_urn` proving it was generated under authorized governance constraints.

---

## 8. Aggregate Analysis

*   **DiscoveryPolicy** (New Aggregate in Governance Context): Defines $Min(ForeignFlow)$, $Max(Volatility)$, $RegimeConstraints$.
*   **StockOverview** (New Read Model): Decoupled from thesis lifecycle.
*   **StockResearch** (New Read Model): Decoupled from raw data structures.

---

## 9. Replayability Analysis (Challenge Area 5)

**Scenario:** 5 years later, Provider corrects historical data, Research was invalidated, Regimes changed 100 times.
**Stress Test Results:** The replay is 100% deterministic.
1.  **Decision** points to `forecast_urn`.
2.  **Forecast** points to `thesis_urn` and `regime_urn`.
3.  **Thesis** points to `research_urn`.
4.  **Research** points to `evidence_urn`.
5.  **Evidence Registry** fetches the exact immutable hash recorded at $T_{-5\text{ years}}$, completely ignoring the Provider's subsequent historical data correction.
**Verdict:** **VALIDATED**. Flawless auditability.

---

## 10. Scalability Analysis

By catching the `StockProjection` God-Projection flaw, we averted severe read-database thrashing. Splitting the view into `Overview` and `Research` drastically reduces payload size and limits the event fan-in blast radius during UI updates.

---

## 11. Security Analysis

Dual-signature authorization remains intact at the `CIO Engine` boundary. No execution can occur without a cryptographic signature matching a valid `DecisionJournal` entry, which itself requires a valid `ThesisVersion`.

---

## 12. Governance Analysis

The discovery of the `Discovery Engine` loophole was critical. By routing `DiscoveryPolicy` ownership to the `Governance Engine`, we ensure that the funnel generating analyst workloads is strictly regulated, auditable, and incapable of stealth-trading.

---

## 13. Failure Analysis

*   **Projection Worker Crash**: Recovers gracefully via standard Kafka offset tracking. UI displays `updated_at` staleness warning.
*   **Provider Outage**: Fails over via `ProviderRegistry`.
*   **Evidence Registry Corruption**: Impossible due to SHA-256 content addressing.

---

## 14. Architecture Delta Analysis

| Component | Pre-Freeze Gate Assumption | Post-Freeze Gate Reality |
|---|---|---|
| **Stock Projection** | Unified `StockProjection` | **Split**: `Overview` and `Research`. |
| **Discovery Thresholds** | Owned by Discovery Engine | **Owned by Governance Engine**. |

---

## 15. ADR Recommendations

The architecture cannot freeze until the following ADRs are drafted and approved:
*   **ADR-102**: Decompose StockProjection into Overview and Research Read Models.
*   **ADR-103**: Assign Discovery Engine Policy Ownership to Governance Engine.

---

## 16. Acceptance Criteria

1.  A change to a `Thesis` MUST NOT trigger a rebuild of the `StockOverviewProjection`.
2.  The `Discovery Engine` MUST reject any execution cycle if the `DiscoveryPolicy` hash does not match an active policy in the `Governance Engine`.
3.  The `Forecast` MUST dynamically update probabilities upon a `RegimeShiftEvent` without forcing the `Thesis` to increment its version.

---

## 17. Freeze Readiness Assessment

The architecture is structurally brilliant in its handling of evidence, forecasts, and replays. However, the `StockProjection` coupling and the `Discovery Governance` loopholes are critical systemic risks. Implementation against this design would lead to immediate operational bottlenecks and governance violations. The architecture must undergo one final revision round to integrate ADR-102 and ADR-103.

---

## 18. Final Verdict

**FREEZE_GATE_FAILED**
