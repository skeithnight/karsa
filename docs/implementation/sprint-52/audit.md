# Final Implementation Compliance Audit

**Status:** IMPLEMENTATION_REQUIRES_REMEDIATION

---

## 1. Executive Summary

This document presents the final compliance audit of `implementation_plan.md` against the frozen Karsa IDX Research Platform architecture (R7-R10). The objective was to identify implementation drift before any code generation or scaffolding begins.

*   **Compliance Score**: 75%
*   **Critical Findings Count**: 2 (Governance Ownership Leak, Missing Universe Domain)
*   **Major Findings Count**: 3 (Missing API Contracts, Missing Event Contracts, Incomplete Schemas)
*   **Minor Findings Count**: 1 (Sprint Wave alignment)
*   **Overall Readiness**: IMPLEMENTATION_REQUIRES_REMEDIATION

The implementation plan failed to capture the `Governance Engine` in its ownership matrix, completely missed the `Research Universes` aggregate assigned to Market Structure, and severely truncated the Event and API contracts required to fulfill the VIF workflows.

---

## 2. Architecture Compliance Matrix

| Decision | Expected | Actual (Impl Plan) | Status | Evidence |
|---|---|---|---|---|
| **ADR-104 (Projections)** | Market, Research, Portfolio | Market, Research, Portfolio | **PASS** | Section 7 matches perfectly. |
| **ADR-105 (Governance)** | Research (Profile), Gov (Guardrail) | Missed Governance Engine | **FAIL** | Section 2 Ownership Matrix omits Governance. |
| **ADR-106 (Foreign Flow)** | Market Structure Engine | Market Structure Engine | **PASS** | Section 15 acknowledges ADR-106. |
| **Forecast Lifecycle** | Follows Thesis | Follows Thesis | **PASS** | Wave 5 & 6 order is correct. |
| **Evidence Promotion** | Tiered Registry | Tiered Registry | **PASS** | Section 5 lists `evidence_registry_manifests`. |
| **Opportunity Discovery** | Profile + Guardrail | Missing Guardrail Event | **FAIL** | Section 6 Event Contracts omits Profile/Guardrail creation. |
| **Research Universes** | Market Structure owns Universes | Missing entirely | **FAIL** | No tables, APIs, or events for Universes. |
| **Frontend Composition** | UI composes 3 domains | UI composes 3 domains | **PASS** | Section 10 Sequence Diagram validates this. |
| **Domain Projection Strategy**| CQRS Event-driven | CQRS Event-driven | **PASS** | Section 7 Refresh Strategy is CDC event-driven. |

---

## 3. Missing Components Matrix

| Component | Owner Context | Missing Artifacts | Severity | Recommended Remediation |
|---|---|---|---|---|
| **Governance Engine** | Governance | Ownership Matrix entry, Rollout Order | **Critical** | Add `src/karsa/governance` to Section 2. |
| **Research Universes** | Market Structure | `UniverseRegistry`, Schemas, Events | **Critical** | Add Universe tracking to Market Structure domain. |
| **Discovery Policies** | Research / Gov | Profile/Guardrail APIs and Events | **Major** | Expand API and Event contracts for Discovery. |
| **Thesis Aggregates** | Thesis Engine | `thesis_hypotheses` schema | **Major** | Add schema mapping for Thesis. |

---

## 4. Missing Schema Matrix

| Table Name | Owner Context | Reason Required | Severity |
|---|---|---|---|
| `governance_guardrails` | Governance | Persist risk limits for Discovery suppression | Critical |
| `market_universes` | Market Structure | Track canonical IDX universes (LQ45, Sectors) | Critical |
| `universe_memberships` | Market Structure | Track exact stock mapping for index rotation | Critical |
| `thesis_versions` | Thesis Engine | Formal hypotheses linking to Research | Major |

---

## 5. Missing Event Contract Matrix

| Event | Producer | Consumer | Payload | Coverage Status |
|---|---|---|---|---|
| `EvidencePromotedEvent` | Evidence Registry | Downstream | `evidence_urn` | **Covered** |
| `ForeignFlowAnomalyDetectedEvent`| Market Structure | Discovery | `asset_id`, `score` | **Covered** |
| `OpportunityIdentifiedEvent` | Discovery | UI / Research | `profile_urn`, `evidence` | **Covered** |
| `DiscoveryProfileCreatedEvent` | Research | Discovery | `profile_urn`, `thresholds` | **MISSING** |
| `DiscoveryGuardrailCreatedEvent`| Governance | Discovery | `guardrail_urn`, `limits` | **MISSING** |
| `ResearchPublishedEvent` | Research | Thesis | `research_urn`, `findings` | **Covered** |
| `ThesisPublishedEvent` | Thesis | Forecast | `thesis_urn`, `hypothesis` | **MISSING** |
| `ForecastGeneratedEvent` | Forecast | UI | `forecast_urn`, `returns` | **Covered** |
| `ForecastUpdatedEvent` | Forecast | UI | `forecast_urn`, `returns` | **MISSING** |
| `UniverseMembershipChangedEvent`| Market Structure | UI / Discovery | `universe_id`, `asset_id` | **MISSING** |
| `UniverseRebalancedEvent` | Market Structure | UI / Discovery | `universe_id`, `composition` | **MISSING** |

---

## 6. Projection Compliance Audit

*   **Projection coupling**: None detected.
*   **Hidden God Projections**: None. The 3 projections (`Market`, `Research`, `Portfolio`) are strictly separated.
*   **Rebuild blast radius**: Isolated per domain.
*   **Ownership violations**: None.
*   **Verdict**: **PASS**. ADR-104 is fully respected in the implementation plan.

---

## 7. Frontend Composition Audit

*   **Query Contracts**: Identified via `GET /market`, `GET /research`, `GET /portfolio`.
*   **React Query Hooks**: Implicit in Section 10 Sequence Diagram.
*   **Cache Boundaries**: Domain-isolated.
*   **Workspace Ownership**: UI purely renders, no business logic leak.
*   **Missing Details**: Missing the `GET /market/universes` query contract required for the Left Panel.

---

## 8. API Coverage Audit

*   **Market APIs**: Missing `GET /api/v1/market/universes`, `GET /api/v1/market/breadth`.
*   **Discovery APIs**: Missing `POST /api/v1/discovery/profiles`, `POST /api/v1/discovery/guardrails`.
*   **Research APIs**: Complete.
*   **Thesis APIs**: Missing `POST /api/v1/thesis/publish`.
*   **Forecast APIs**: Complete.
*   **Portfolio APIs**: Complete.
*   **Evidence APIs**: Missing historical resolution API (`GET /api/v1/evidence/{urn}`).
*   **Search APIs**: Missing `GET /api/v1/search/assets`.

---

## 9. Wave-by-Wave Gap Analysis

*   **Wave 1-3**: Missed Universe definition inside Market Structure.
*   **Wave 4 (Discovery)**: Governance Engine was improperly collapsed into the Discovery wave. Governance must be explicitly scaffolded.
*   **Wave 5 (Research & Thesis)**: Missed `ThesisPublishedEvent`.
*   **Wave 6-12**: Structurally sound, but will fail E2E tests without the APIs missed in Wave 4.

---

## 10. Read Model Audit

*   **MarketProjection**: Missing `Universes`.
*   **ResearchProjection**: Missing `Guardrails` (required for transparency in why opportunities were suppressed).
*   **PortfolioProjection**: Compliant.

---

## 11. Governance Audit

*   **Ownership Leaks**: The implementation plan collapsed Governance into `Wave 4 (Discovery & Governance)` but failed to allocate a backend directory or schema owner to `Governance Engine`. This is a hard violation of ADR-105.
*   **Missing Services**: `GovernancePolicyService` is missing from the API and schema rollout.

---

## 12. Foreign Flow Ownership Audit

*   **Verification**: ADR-106 is strictly respected. The plan explicitly places Foreign Flow intelligence solely inside `src/karsa/market_structure`. No ownership violations exist.

---

## 13. Evidence Lineage Audit

*   **Verification**: `provider_datalake_blobs` $\to$ `evidence_registry_manifests` $\to$ Downstream.
*   **Missing Links**: The `GET /api/v1/evidence/{urn}` endpoint is missing. Without a retrieval API, Post-Mortems cannot physically fetch the payload hash from the registry during an audit.

---

## 14. Remediation Plan

**Critical Remediations:**
1.  **Extract Governance Context**: Explicitly add `src/karsa/governance`, `governance_guardrails` table, and `DiscoveryGuardrailCreatedEvent`. Owner: Infrastructure/Backend. Blocking: YES.
2.  **Add Universe Domain**: Explicitly add `market_universes` schemas and APIs to `src/karsa/market_structure`. Owner: Backend. Blocking: YES.

**Major Remediations:**
1.  **Expand API Contracts**: Add the missing Search, Evidence Retrieval, and Thesis Publish endpoints. Owner: Backend. Blocking: YES.
2.  **Expand Event Contracts**: Add the missing Universe and Forecast progression events. Owner: Backend. Blocking: YES.

---

## 15. Updated Implementation Plan Delta

**New Schemas:**
*   `governance_guardrails` (Owner: Governance Engine)
*   `market_universes`, `universe_memberships` (Owner: Market Structure)
*   `thesis_versions` (Owner: Thesis Engine)

**New APIs:**
*   `GET /api/v1/evidence/{urn}`
*   `POST /api/v1/thesis/publish`
*   `POST /api/v1/discovery/guardrails` (Governance Engine)
*   `GET /api/v1/market/universes`
*   `GET /api/v1/search/assets`

**New Events:**
*   `DiscoveryProfileCreatedEvent`, `DiscoveryGuardrailCreatedEvent`
*   `ThesisPublishedEvent`, `UniverseMembershipChangedEvent`

---

## 16. Architecture Compliance Verdict

**IMPLEMENTATION_REQUIRES_REMEDIATION**

**Justification:** While the plan successfully implemented the heavy structural CQRS and VIF boundaries (ADR-104, 106, Evidence Tiering), it suffered from major implementation drift by silently dropping the `Governance Engine` as a distinct bounded context and completely ignoring the `Research Universes` functionality introduced in Round 7. These omissions guarantee that the code will not meet the frozen architecture's requirements. 

---

## 17. Final Execution Recommendation

**Remediation Execution Order:**

1.  **Update Implementation Plan**: Apply the deltas from Section 15. Explicitly inject the `Governance Engine` into the Ownership Matrix.
2.  **Update Schema Rollout**: Add Universe and Governance tables.
3.  **Update API Rollout**: Add the 5 missing REST endpoints.
4.  **Resubmit**: After remediation, the plan will be automatically elevated to `IMPLEMENTATION_READY`.

No code generation is authorized until the implementation plan incorporates these remediations.
