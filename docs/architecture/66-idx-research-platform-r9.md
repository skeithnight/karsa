# 66. Karsa IDX Research Platform - Round 9 Architecture Attack

**Status:** ARCHITECTURE_REQUIRES_REVISION

---

## 1. Executive Summary

This document captures the ninth round of architecture challenges for the Karsa IDX Research Platform. The mandate was to aggressively re-attack the remediations proposed in Round 8 (ADR-102 and ADR-103) to ensure we were not simply swapping one architectural flaw for another.

The attack successfully broke the Round 8 assumptions. Attempting to split the Stock Projection into "Overview" and "Research" merely created two smaller God Projections. Similarly, handing `DiscoveryPolicy` entirely to the Governance Engine improperly turned Governance into a Research proxy. By enforcing strict domain-aligned projections and splitting Discovery ownership into `Profiles` (Research) and `Guardrails` (Governance), the architecture finally achieves mathematically perfect bounded context isolation.

Because ADR-102 and ADR-103 failed the attack and require replacement, the architecture is not ready for freeze. The verdict is **ARCHITECTURE_REQUIRES_REVISION**.

---

## 2. Ownership Boundary Matrix

| Domain / Subsystem | Current Round 8 Owner | New Round 9 Owner | Justification |
|---|---|---|---|
| **Stock UI Projection** | Read Model Platform | **Frontend (Composition)** | Backend projections must mirror domains, not UI pages. |
| **Discovery Criteria** | Governance Engine | **Research Engine** | Research dictates what an "Opportunity" is. |
| **Discovery Guardrails** | Governance Engine | **Governance Engine** | Governance dictates what anomalies are legally prohibited from triggering workloads. |
| **Foreign Flow Intel** | Ambiguous | **Market Structure Engine** | Foreign Flow is structurally identical to Market Breadth calculations. |

---

## 3. Projection Ownership Analysis (Challenge Area 1)

**Attack:** Is splitting `StockProjection` into `StockOverviewProjection` and `StockResearchProjection` just creating smaller God Projections? 
**Analysis:** Yes. Any projection named "Stock" inherently attempts to aggregate across all domains for a single entity, forcing tight coupling. The backend must project *Domains*, not *Entities*.
**Evaluation:** Option B. The backend produces `MarketProjection`, `ResearchProjection`, and `PortfolioProjection`.
**Final Recommendation:** The UI (Frontend) becomes the composition layer. The `Hybrid Terminal` UI independently fetches `IDX:BBCA` from the three separate domain projections and stitches them together client-side. 
*Replaces ADR-102.*

---

## 4. Discovery Ownership Analysis (Challenge Area 2)

**Attack:** Does handing `DiscoveryPolicy` to the Governance Engine turn it into a Research Engine?
**Analysis:** Yes. If the Governance Engine sets the rules for identifying "Foreign Flow Anomalies," it is effectively doing quantitative research. Governance's role is risk management, not alpha generation.
**Evaluation:** Option C. 
1.  **Research Engine** owns `DiscoveryProfile` (e.g., Alert when Foreign Flow > 3 StdDev).
2.  **Governance Engine** owns `DiscoveryGuardrails` (e.g., Suppress all alerts for companies with Market Cap < 50B IDR).
3.  **Discovery Engine** executes both, discarding any `Profile` match that violates a `Guardrail`.
**Final Recommendation:** Option C.
*Replaces ADR-103.*

---

## 5. Foreign Flow Ownership Analysis (Challenge Area 3)

**Attack:** Who owns Foreign Flow intelligence?
**Analysis:** The Provider Platform fetches the raw net buy/sell numbers. However, determining if that number represents "Accumulation" or "Distribution" relative to historical volume is a structural market calculation.
**Evaluation:** Option B. The `Market Structure Engine` natively owns Market Breadth and Sector Rotation. Foreign Flow intelligence is mathematically identical in its purpose: to contextualize raw ticker data.
**Final Recommendation:** Foreign Flow Intelligence is formally housed within the `Market Structure Engine` bounded context.

---

## 6. Workspace Composition Analysis (Challenge Area 4)

**Attack:** Should backend projections mirror UI pages?
**Analysis:** Absolutely not. Projection-per-page (Option A) creates God Projections that rebuild endlessly. 
**Evaluation:** Option B (Projection-per-domain). The UI fetches independently from the decomposed domain projections. This drastically lowers cognitive load for backend engineers while maximizing read scalability. If the `Research Engine` schema changes, the `MarketProjection` remains 100% unaffected.
**Final Recommendation:** Option B.

---

## 7. Event Contract Analysis

*   `DiscoveryProfileCreatedEvent`: Emitted by Research Engine. Defines analytical anomaly thresholds.
*   `DiscoveryGuardrailCreatedEvent`: Emitted by Governance Engine. Defines firm-wide suppression rules.
*   `OpportunityIdentifiedEvent`: Emitted by Discovery Engine. Must embed BOTH `profile_urn` and `guardrail_urn` to prove authorized generation.
*   `ForeignFlowAnomalyDetectedEvent`: Emitted by Market Structure Engine. Consumed by Discovery Engine.

---

## 8. Replayability Analysis

Replayability is mathematically preserved. To replay a historical `OpportunityIdentifiedEvent`, the system fetches the `profile_urn` (What the analyst was looking for), the `guardrail_urn` (What the firm allowed), and the `evidence_urn` (The exact Foreign Flow snapshot from the Evidence Registry). 

---

## 9. Scalability Analysis

By shifting "Stock" composition to the Frontend UI, the backend Read Model Platform achieves ultimate scalability. `ResearchProjection` rebuilds are now isolated exclusively to Research events. The blast radius of an event is contained perfectly within its domain.

---

## 10. Governance Analysis

The separation of `DiscoveryProfile` (Research) and `DiscoveryGuardrails` (Governance) perfectly maps to a real-world Virtual Investment Firm. The Analysts hunt for anomalies, while the Chief Risk Officer places bounds on what they are allowed to look at. This prevents the Discovery Engine from generating rogue signals.

---

## 11. VIF Integrity Audit (Challenge Area 5)

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| **Discovery $\to$ Signal Engine** | Zero | High | Prevented by Governance Guardrails and absence of Execution integration. |
| **Research $\to$ Recommendation** | Zero | High | Prevented by Option B (Strict Findings Contract). |
| **Forecast $\to$ Decision** | Zero | Critical | Prevented by CIO dual-signature authorization. |
| **Watchlist $\to$ Research** | Zero | Medium | Watchlist is strictly Frontend UI state; Research relies on Market Structure Universes. |
| **Foreign Flow $\to$ Trading Signal**| Zero | High | Owned by Market Structure as analytical context, not actionable execution. |

---

## 12. Architecture Delta Analysis

| Component | Round 8 Proposal | Round 9 Reality |
|---|---|---|
| **UI Projections** | `StockOverview` & `StockResearch` | **Domain Projections** stitched by Frontend UI. |
| **Discovery Rules** | Governance Engine entirely | **Split**: Profiles (Research) vs Guardrails (Governance). |
| **Foreign Flow** | Ambiguous / UI Layer | **Market Structure Engine**. |

---

## 13. ADR Recommendations

Round 8's proposed ADR-102 and ADR-103 are formally rejected. They are replaced by:
*   **ADR-104**: Domain-Aligned Projections with Frontend Composition (Replaces ADR-102).
*   **ADR-105**: Bipartite Discovery Governance (Profiles vs Guardrails) (Replaces ADR-103).
*   **ADR-106**: Foreign Flow Intelligence Ownership mapped to Market Structure.

---

## 14. Acceptance Criteria

1.  A UI Page request MUST NOT query a backend aggregate projection; it MUST fetch from independent domain projections concurrently.
2.  An `OpportunityIdentifiedEvent` MUST fail validation if it lacks a valid `guardrail_urn`.
3.  Raw Foreign Flow data MUST NOT bypass the `Market Structure Engine`.

---

## 15. Freeze Readiness Assessment

Round 8 accurately identified two massive flaws, but its proposed solutions (ADR-102, ADR-103) were structurally incorrect. Round 9 successfully broke those solutions and replaced them with domain-aligned, highly scalable alternatives. The architecture is mathematically sound, but because three new fundamental ADRs (104, 105, 106) have been generated, the architecture cannot yet freeze.

---

## 16. Final Verdict

**ARCHITECTURE_REQUIRES_REVISION**
