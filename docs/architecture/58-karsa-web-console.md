# Karsa Web Console Architecture (Sprint-51)

## 1. Executive Summary
The Sprint-51 Karsa Web Console architecture has undergone a final hostile validation to ensure it truly embodies a Virtual Investment Firm interface rather than a generic engineering administration portal. By scrutinizing operator workflows through the lens of a Chief Investment Officer (CIO), the architecture has been refined to elevate investment narratives, rank algorithmic conviction, decouple intelligence timelines, and adopt formal asset management nomenclature. Crucially, the scope has been aggressively partitioned to protect Sprint-51 execution velocity while cementing a visionary roadmap for subsequent iterations.

## 2. Architecture Validation Findings
* **Lack of Executive Perspective**: The prior iteration provided excellent investigative tools (Thesis Detail) but lacked a true top-down "CIO Dashboard" to instantly surface what matters today.
* **Information Overload**: Treating all active theses equally hindered prioritization; a distinct ranking/sorting UI capability was missing.
* **Nomenclature Mismatch**: Terminology like "Workers" and "Research Runs" felt distinctly computational rather than financial ("Analysts", "Research Reports").
* **Scattered Governance**: Post-mortems and systematic reviews were relegated to sub-views rather than treated as a primary feedback loop requiring a dedicated workspace.

## 3. CIO Workspace Analysis
* **Challenge Result**: Accepted. The `Portfolio Console` is insufficient as a landing page because it focuses solely on current accounting.
* **Design Decision**: A dedicated `CIO Dashboard` will serve as the primary entry point. It instantly answers:
  1. What are the highest conviction ideas generated today?
  2. Which active theses are approaching invalidation?
  3. Which analysts (workers) are leading in alpha generation?
  4. What capital allocation shifts occurred in the last 24h?

## 4. Thesis Ranking Analysis
* **Challenge Result**: Accepted. An unranked list of active theses provides no actionable insight to a human operator.
* **Design Decision**: `Thesis Ranking` is promoted to a first-class UI capability within the Thesis Workspace. The UI will implement complex, multi-factor sorting tables powered by AG Grid, allowing the operator to sort by:
  * Top Conviction (Signal Fidelity)
  * Highest Expected Return
  * Most Undervalued (via underlying Research logic)
  * Highest Risk (Volatility exposure)
  * Recently Upgraded / Degraded

## 5. Watchlist Analysis
* **Challenge Result**: Accepted but Deferred.
* **Design Decision**: The ability to monitor a ticker prior to formal thesis generation is critical. However, the backend engines (Research/Thesis) must first natively support a "passive monitoring" bounded context before the UI can render it. 
* **Action**: Added to Future Evolution. The UI will eventually support a `Watchlist Workspace` allowing manual ticker injection for autonomous monitoring.

## 6. Timeline Analysis
* **Challenge Result**: Accepted. Entity-centric navigation hides the systematic momentum of the firm.
* **Design Decision**: An `Intelligence Timeline` component will be embedded within the CIO Dashboard and globally accessible. It streams a unified chronological feed:
  * `09:00` Research Report Published (AAPL)
  * `09:05` High-Conviction Thesis Generated (LONG AAPL)
  * `09:15` Investment Memo Generated (Decision)
  * `09:16` Capital Allocated (Portfolio)

## 7. Decision Journal UX Analysis
* **Challenge Result**: Accepted. The UI must expose the ex-ante reasoning before hindsight bias sets in.
* **Design Decision**: The Decision Journal will be rebranded as the `Investment Memos` workspace. Memos will prominently feature:
  * Systematic Intent
  * Expected Horizon
  * Confidence Interval
  * Hard Invalidation Criteria

## 8. Review Workspace Analysis
* **Challenge Result**: Accepted.
* **Design Decision**: A dedicated `Investment Oversight` workspace will centralize all Governance feedback loops. It will expose a macro view of systematic errors:
  * Most frequent invalidation causes.
  * Analysts with the highest failure rates in specific regimes.
  * Post-Mortem reports linked directly to the offending Investment Memos.

## 9. Attribution UX Analysis
* **Challenge Result**: Accepted. Simple P&L is insufficient.
* **Design Decision**: The `Performance & Attribution` workspace will visualize the distinct decomposition of returns using stacked area charts (Tremor/Recharts). Operators will distinctly see the ratio of:
  * Selection vs Allocation vs Execution vs Beta vs Residual.

## 10. Capital Allocation Analysis
* **Challenge Result**: Accepted but Partitioned.
* **Design Decision**: The UI must eventually answer *why* capital is deployed in specific ratios. Sprint-51 will surface *where* capital is allocated. Exposing the deep parametric reasoning of *why* the Execution/Portfolio engine chose those weights will be deferred to a dedicated Sprint-53 Capital Allocation UX initiative.

## 11. Product Identity Analysis
* **Challenge Result**: Accepted. Terminology must reflect a Virtual Investment Firm.
* **Changes Enacted**:
  * Workers → **Analysts** (e.g., Bull Analyst, Bear Analyst)
  * Research Runs → **Research Reports**
  * Decision Journal → **Investment Memos**
  * Performance Console → **Performance & Attribution**
  * Governance Console → **Investment Oversight**
  * System Administration → **Infrastructure Health**

## 12. Scope Classification Matrix
| Capability | Scope Classification | Justification |
|---|---|---|
| CIO Dashboard | Sprint-51 Must Have | Essential landing experience for product identity. |
| Product Identity Updates | Sprint-51 Must Have | Zero engineering cost; purely UI semantic mapping. |
| Thesis Ranking (Data Grids) | Sprint-51 Must Have | Solved out-of-the-box via AG Grid implementation. |
| Intelligence Timeline | Sprint-51 Nice To Have | Dependent on backend event aggregation capabilities. |
| Attribution Visualization | Sprint-51 Nice To Have | Dependent on complex Recharts implementation. |
| Watchlist Workspace | Sprint-52+ | Requires core engine backend support first. |
| Deep Capital Allocation Reasoning | Future Evolution | Requires extensive Execution Engine query projections. |
| Knowledge Graph Explorer | Future Evolution | High frontend rendering complexity. |

## 13. Architecture Delta Analysis
* Rebranded all navigation elements and components to match the Virtual Investment Firm nomenclature.
* Added the `CIO Dashboard` as the application root (`/`).
* Merged Performance and Attribution into a unified `Performance & Attribution` workspace.
* Promoted Governance to `Investment Oversight` with dedicated Post-Mortem macro analytics.
* Re-scoped complex visual topologies (Graphs, Watchlists) to future sprints to guarantee Sprint-51 delivery.

## 14. ADR Impact Analysis
* **ADR-076**: Adopt Virtual Investment Firm Nomenclature in all UI and UX constructs.
* **ADR-077**: Establish the CIO Dashboard as the primary entry point over the abstract Portfolio aggregate.

## 15. Updated Acceptance Criteria
1. The application mounts the CIO Dashboard at the root path (`/`).
2. Navigation relies strictly on financial terminology (Analysts, Investment Memos, Investment Oversight).
3. Thesis Ranking is available via interactive column sorting on the Thesis Workspace.
4. The application continues to compile statically without server-side rendering dependencies.
5. All underlying API data mapping aligns with the renamed frontend concepts.

## 16. Final Verdict
**ARCHITECTURE_APPROVED**
**ARCHITECTURE_FROZEN**
