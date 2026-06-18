# 63. Karsa IDX Research Platform - Architecture Challenge Round 6

**Status:** ARCHITECTURE_REQUIRES_REVISION

---

## 1. Executive Summary

This document details the sixth round of architecture challenges for the Karsa IDX Research Platform. The mandate was to aggressively attack the existing boundaries, assumptions, and lifecycles without bias. 

The attack successfully exposed critical systemic flaws. The previous lifecycle incorrectly placed Forecast *before* Thesis, allowing forecasts to exist without a formalized hypothesis boundary. The `InvestmentIntelligenceProjection` was identified as a monolithic "God Projection" that creates operational bottlenecks. Furthermore, treating all raw provider data as immutable evidence guarantees an unsustainable storage crisis. 

Because these flaws violate strict CQRS scalability and Virtual Investment Firm accountability, the architecture must be revised. The final verdict is **ARCHITECTURE_REQUIRES_REVISION**.

---

## 2. Ownership Boundary Matrix

| Domain / Subsystem | New Proposed Owner | Change from R5 |
|---|---|---|
| **Raw Provider Datalake** | Provider Platform | Separated from Evidence Registry |
| **Research-Grade Evidence** | Evidence Registry | Must be explicitly "promoted" from Datalake |
| **Research Universes (LQ45)**| Market Structure Engine | Formally separated from User Watchlists |
| **User Watchlists** | UI Preferences | No change |
| **Opportunity Discovery** | Discovery Engine | New domain introduced |
| **Forecasts** | Forecast Engine | Dependency inverted (Requires Thesis) |

---

## 3. Forecast Lifecycle Analysis

**Challenge**: Can Forecast logically exist before Thesis? 
**Analysis**: No. A Forecast requires a specific time horizon, invalidation criteria, and contextual assumptions to have any meaning. Predicting a 20% return is useless unless it is strictly bound to a specific Hypothesis (e.g., "Because CASA share grows 5%").

**Recommendation: Option B**
*Pipeline*: `Evidence` $\to$ `Research` $\to$ `Thesis` $\to$ `Forecast` $\to$ `Decision`
A `Thesis` must be established first to define the boundaries of the `Forecast`. The `Forecast` then explicitly projects the probability and returns of that specific `Thesis`.

---

## 4. Projection Strategy Analysis

**Challenge**: Does `InvestmentIntelligenceProjection` become a God Projection?
**Analysis**: Yes. Aggregating 7 distinct bounded contexts into a single projection violates CQRS read-model segregation. A single delayed `Attribution` event would invalidate the entire `InvestmentIntelligence` cache, forcing a massive, expensive rebuild of data that hasn't changed (e.g., Market Structure).

**Recommendation: Option B**
Split the God Projection into aligned views:
1. `MarketIntelligenceProjection`
2. `ResearchIntelligenceProjection`
3. `PortfolioIntelligenceProjection`

---

## 5. Market Structure Analysis

**Challenge**: Determine the nature of Market Structure.
**Analysis**: Market Structure owns complex aggregations (Breadth, Relative Strength, Sector Rotation) derived from raw data. It possesses business logic specific to VIFs.

**Recommendation: Option C (First-Class Bounded Context)**
Market Structure generates domain events (e.g., `SectorRotationDetectedEvent`). It owns the `MarketStructureSnapshot` aggregate.

---

## 6. Evidence Registry Analysis

**Challenge**: Should the Evidence Registry store all raw OHLCV and daily ticks?
**Analysis**: Storing all ticks as immutable, hashed artifacts will cause an uncontrollable storage explosion. Raw ticks are simply data; they only become *Evidence* when an Analyst relies on them to formulate a viewpoint.

**Recommendation: Option C (Tiered Evidence Strategy)**
The Provider Platform maintains a transient, raw datalake. The `Evidence Registry` only stores data that has been explicitly **promoted** (e.g., locking a snapshot of the PER chart specifically at the moment an `AnalystReport` is drafted).

---

## 7. Watchlist Analysis

**Challenge**: Separation of Personal Watchlist vs Research Universe.
**Analysis**: 
*   **Personal Watchlist** (BBCA, TLKM): UI preference. Belongs to the user profile.
*   **Research Universe** (LQ45, IDX-Finance): A canonical platform grouping used for relative valuation.

**Recommendation**: The `Market Structure Engine` formally owns Research Universes as aggregates. User Preferences continue to own Watchlists.

---

## 8. Discovery Layer Analysis

**Challenge**: How does Research organically discover opportunities without manually opening 800 stocks?
**Analysis**: Relying on Analysts to manually scan the IDX is inefficient. Relying on a system to generate Buy/Sell signals violates the VIF human-in-the-loop requirement.

**Recommendation: Option B (Opportunity Discovery Engine)**
An engine that subscribes to `MarketStructureSnapshot`s and emits `OpportunityIdentifiedEvent`s based on structural anomalies. It acts purely as a funnel for the `Research Engine`, strictly forbidden from emitting trading decisions.

---

## 9. UX Analysis

**Challenge**: Is the 5-Workspace model too fragmented for an MVP?
**Analysis**: For a new VIF, forcing a CIO/Analyst to context-switch across 5 full-page workspaces to execute a single workflow induces high cognitive load and friction. 

**Recommendation: Option C (Hybrid Terminal for MVP)**
A single-page Master-Detail IDX Research Terminal that acts as a UI aggregator of the three new projections (`MarketIntelligence`, `ResearchIntelligence`, `PortfolioIntelligence`). This satisfies MVP usability while preserving the strict backend CQRS separation.

---

## 10. Replayability Analysis

*   **Flaw Found**: In R5, raw data was assumed to be Evidence. By introducing "Evidence Promotion", replayability is actually strengthened. We now only replay the *exact* subset of data the analyst promoted, rather than trying to reconstruct the entire IDX tick state.

---

## 11. Scalability Analysis

*   **Flaw Found**: The God Projection would have failed under load due to continuous invalidation. Splitting projections limits rebuilds strictly to the domain that updated.
*   **Flaw Found**: The Evidence Registry would have exhausted storage. Evidence Promotion guarantees $O(\text{Research Activity})$ growth rather than $O(\text{Market Ticks})$ growth.

---

## 12. Auditability Analysis

Moving `Forecast` behind `Thesis` guarantees that every expected return and probability score has a legally binding set of assumptions tied to it before the `CIO Engine` is allowed to see the forecast.

---

## 13. Risk Register

*   **Complexity**: Introducing the Discovery Engine adds another moving part before Research can begin.
*   **Data Lineage**: Evidence Promotion requires a robust UI mechanism for analysts to "snapshot" their screens/data queries accurately into the Evidence Registry.

---

## 14. ADR Recommendations

*   **ADR-098**: Split God Projection into Domain-Aligned Read Models.
*   **ADR-099**: Invert Forecast Lifecycle to depend on Formal Thesis Formulation.
*   **ADR-100**: Adopt Tiered Evidence Promotion to prevent Storage Exhaustion.
*   **ADR-101**: Introduce Opportunity Discovery Engine as an Analyst Funnel.

---

## 15. Architecture Delta Analysis

| Component | R5 Status | R6 Status |
|---|---|---|
| **Forecast** | Precedes Thesis | **Follows Thesis**. |
| **UI Projection** | Monolithic God Projection | **Fragmented Domain Projections**. |
| **Evidence** | All Provider Data | **Promoted Snapshots Only**. |
| **Discovery** | Manual | **Opportunity Discovery Engine**. |
| **Universes** | UI Watchlist | **Market Structure Aggregate**. |

---

## 16. Freeze Readiness Assessment

The architecture is **NOT** ready for freeze. The attack exposed critical flaws in the lifecycle pipeline, data storage scaling, and read-model operational overhead. These revisions fundamentally alter the sequence of events leading to a Decision. The proposed ADRs (098-101) must be drafted and integrated into the core topology before freeze can be granted.

---

## 17. Final Verdict

**ARCHITECTURE_REQUIRES_REVISION**
