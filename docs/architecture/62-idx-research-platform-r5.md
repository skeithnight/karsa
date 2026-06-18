# 62. Karsa IDX Research Platform - Architecture Challenge Round 5

**Status:** IMPLEMENTATION_READY

---

## 1. Executive Summary

This document concludes the fifth and final architecture challenge round for the Karsa IDX Research Platform. The objective was to relentlessly attack the final ambiguous boundaries: projection ownership, the dichotomy between the Event Journal and Evidence Registry, and the contract bridging Research and Thesis.

Through rigorous challenge loops, infrastructure was stripped of domain ownership, the Evidence Registry was explicitly firewalled from the CQRS Event Journal, and Research was restricted from leaking investment recommendations into the Thesis. The architecture has resolved all systemic flaws and is now certified as **IMPLEMENTATION_READY**.

---

## 2. Ownership Boundary Matrix

| Domain / Subsystem | Canonical Owner | Core Responsibility |
|---|---|---|
| **Investment Intelligence** | Read Model Platform | Owns denormalized, UI-optimized read projections. |
| **System Events** | CQRS Event Journal | Owns chronological transitions of internal VIF state. |
| **External Facts** | Evidence Registry | Owns content-addressable hashes of immutable external data. |
| **Analytical Synthesis** | Research Engine | Owns `Findings` and `Viewpoints` (No recommendations). |
| **Formal Hypothesis** | Thesis Engine | Owns `Hypothesis`, `Conviction`, and `Invalidation Criteria`. |

---

## 3. ADR-095: Investment Intelligence Projection Ownership

*Refer to `docs/adr/ADR-095-investment-intelligence-projection-ownership.md` for full context.*

**Decision:** The projection is renamed from `StockIntelligenceProjection` to `InvestmentIntelligenceProjection`. Ownership is transferred from the "Projection Worker" (infrastructure) to the **Read Model Platform** (bounded context). 
**Justification:** Infrastructure cannot own business concepts. By abstracting to `InvestmentIntelligence`, the identical schema can project Stocks, Sectors, and Macro Themes without schema redesigns.

---

## 4. ADR-096: Evidence Registry vs Event Journal Boundary

*Refer to `docs/adr/ADR-096-evidence-registry-vs-event-journal.md` for full context.*

**Decision:** The Event Journal exclusively records internal state transitions. The Evidence Registry exclusively stores external payloads as immutable, content-addressable hashes (`evidence_urn`).
**Justification:** Prevents the Event Journal from bloating with gigabytes of raw tick data. If a provider corrects a historical print, the Evidence Registry generates a *new* hash, and the Research Engine emits a new internal event noting the correction, preserving total chronological auditability.

---

## 5. ADR-097: Research Findings → Thesis Contract

*Refer to `docs/adr/ADR-097-research-findings-thesis-contract.md` for full context.*

**Decision:** Option B (Research produces Findings). Research is strictly prohibited from generating "Buy/Sell" recommendations or defining execution constraints.
**Justification:** If Research defines recommendations, Thesis becomes a rubber-stamp, destroying the VIF hierarchy. Research publishes `Findings`; Thesis consumes `Findings` to forge a formal `Hypothesis`.

---

## 6. Investment Intelligence Projection Analysis

Renaming to `InvestmentIntelligenceProjection` ensures scalability beyond individual stocks. 
*   **Scalability**: A Sector projection is identical in schema to a Stock projection (Breadth, Rotation, Analyst Consensus).
*   **Extensibility**: Adding Macro Themes (e.g., "EV Supply Chain") natively fits this read model.
*   **Replay**: Projection rebuilding is identical; CDC replays domain events to rebuild the materialized view.

---

## 7. Event Journal vs Evidence Registry Analysis

*   **System of Record**: Event Journal is the SoR for *actions* (Decisions, Approvals). Evidence Registry is the SoR for *facts* (PER=12.5).
*   **Immutability**: Both are append-only.
*   **Post-Mortem / Attribution**: Post-Mortems query the Event Journal to construct the timeline, then resolve the embedded `evidence_urn`s against the Evidence Registry to view the exact data the Analyst saw at $T_0$.

---

## 8. Research → Thesis Contract Analysis

**Boundary Crossing:**
*   **Research Publishes**: `{ research_urn, findings, evidence_urns, analyst_viewpoints }`
*   **Thesis Consumes**: `{ research_urn }`
*   **Thesis Publishes**: `{ thesis_urn, hypothesis, invalidation_rules, risk_bounds }`
*   **Can multiple Theses originate from one Research artifact?** Yes (e.g., Bull Analyst and Bear Analyst read the same macro Research Report).

---

## 9. Workspace Mapping Matrix

| VIF Workflow Stage | Optimal UI Workspace |
|---|---|
| Stock Discovery & Watchlists | **Stock Workspace** |
| Provider Data / Market Structure | **Market Workspace** |
| Analyst Synthesis / Reports | **Research Workspace** |
| Forecasts & Thesis Generation | **Research Workspace** |
| Decisions & Allocations | **Portfolio Workspace** |
| Outcome Tracking & Post-Mortem | **Learning Workspace** |

**Conclusion:** The workspaces are perfectly aligned. Stock Workspace is an entity-centric jumping-off point. Research handles the heavy analytical lifting.

---

## 10. Signal Engine Assessment

**Assessment:** A future `Signal Engine` sitting between Market Structure and Research.
*   **Purpose**: Generate candidate opportunities from structural metrics.
*   **Scalability**: High. It filters noise before analysts process data.
*   **VIF Violation?**: No, as long as it outputs `Findings` and not `Decisions`.
*   **Recommendation**: **Future Sprint**. It is not required for the MVP, which relies on Analysts manually screening Market Structure data.

---

## 11. Scalability Analysis

The explicit decoupling of the Evidence Registry from the Event Journal removes the primary scalability bottleneck (payload bloat in the Kafka/PostgreSQL bus). Projection ownership by the Read Model Platform guarantees UI load does not degrade Core Domain write performance.

---

## 12. Replayability Analysis

Perfect determinism achieved. A replay at $T_{+5 years}$ requests the Event Journal state up to $T_0$. The historical events reference specific `evidence_urn` hashes. The Evidence Registry returns the exact bytes stored at $T_0$, ignoring any $T_{+1}$ provider corrections.

---

## 13. Auditability Analysis

Strict enforcement of Option B (Research produces Findings) guarantees that an Auditor reviewing a failed trade can trace the `Decision` back to the `Thesis Hypothesis`, back to the `Research Finding`, back to the `evidence_urn`, back to the exact `Provider API payload`.

---

## 14. Risks

*   **Projection Schema Drift**: Unifying Stocks, Sectors, and Themes under `InvestmentIntelligenceProjection` might force sparse schemas if the entity types diverge wildly over time.
    *   *Mitigation*: The projection is JSONB. The frontend safely ignores null properties.

---

## 15. Architecture Delta Analysis

| Component | Round 4 Status | Round 5 (Final) Status |
|---|---|---|
| **Projections** | Owned by Worker | **Owned by Read Model Platform**. Renamed to `InvestmentIntelligence`. |
| **Evidence** | Loosely coupled | **Strictly decoupled from Event Journal**. |
| **Research Output** | Vague "Conclusions" | **Strictly "Findings"**. Recommendations banned. |

---

## 16. Freeze Readiness Assessment

Every assumption, boundary, and data payload has been aggressively attacked over five review rounds. The architecture prevents retail stock-screener regressions, enforces institutional accountability, isolates infrastructure from domain concepts, and guarantees perfect cryptographic replayability. No critical flaws remain. Architecture work must stop to allow engineering execution.

---

## 17. Final Verdict

**IMPLEMENTATION_READY**
