# 59. Karsa IDX Research Platform Architecture Discovery

**Status:** ARCHITECTURE_DISCOVERY

---

## Phase 0: Repository Alignment Review

### 1. Existing Bounded Contexts
Karsa operates on a strict Event-Driven CQRS Architecture with the following active bounded contexts:
- **Capital Allocation**: Optimizes weights and risk budgets.
- **CIO Engine**: Authoritative decision-maker, signs payloads, enforces ledger.
- **Governance Engine**: Evaluates limits, issues exception tokens.
- **Decision Journal**: Write-once registry of pre-outcome reasoning.
- **Thesis Engine**: Immutable hypothesis registry, versioning, and invalidation rules.
- **Performance & Attribution Engine**: Return decomposition and Brier score calibration.
- **Regime Engine**: Market state classification (Bull, Bear, Volatility).
- **Review & Post-Mortem Engine**: Audit convergence and learning.

### 2. CQRS & Event Journal Architecture
- **State**: The platform uses zero mutable aggregate roots for its core control plane (e.g., `cio_decisions`).
- **Events**: Driven by explicitly structured schemas (e.g., `PortfolioDecisionMadeEvent`).
- **Persistence**: Append-only PostgreSQL ledgers protected by database-level triggers blocking `UPDATE` and `DELETE`.

### 3. Compatibility Matrix

| Component | Status | Action | Justification |
|---|---|---|---|
| Thesis Engine | Compatible | Reuse / Extend | Natively supports hypotheses; needs IDX entity types. |
| Regime Engine | Compatible | Reuse / Extend | Currently supports generic segments; extend for IHSG / Sectors. |
| CIO Engine | Compatible | Reuse | Portfolio orchestration is market-agnostic. |
| Decision Journal | Compatible | Reuse | Reason capturing works identically for IDX. |
| Karsa Web Console | Compatible | Extend | Sprint-51 established CIO dashboards; needs IDX Research Workspace addition. |

### 4. Conflict Matrix

| Area | Conflict Risk | Resolution |
|---|---|---|
| Market Data Ingestion | High | Avoid building real-time ticker engines. Rely on EOD data and aggregate snapshots to prevent overwhelming the CQRS bus. |
| Watchlist Lifecycle | Medium | Watchlists are passive. Must not pollute active Thesis ledgers. Require a new `PassiveMonitoring` context. |

### 5. Technical Debt Implications
Introducing IDX specific ingestion will stress the `providers` module. The provider abstraction (ADR-018) must strictly isolate raw IDX vendor APIs from domain aggregates.

---

## Phase 1: Challenge the Product Idea

1. **Why is this better than Stockbit?** Stockbit provides raw data and social sentiment. Karsa forces every insight into a versioned, verifiable Thesis and grades the outcome mechanically.
2. **Why is this better than RTI?** RTI is a real-time terminal. Karsa is a Virtual Investment Firm OS. RTI shows you what is happening; Karsa proves *why* you decided to act on it.
3. **Why is this better than TradingView?** TradingView is for charting. Karsa is for institutional memory and deterministic attribution.
4. **What unique capability does Karsa provide?** The Decision Journal and Post-Mortem learning loop. No retail platform grades ex-ante confidence against ex-post reality.
5. **Which information is merely market data?** Ticker prices, RSI values, raw PER, daily volume.
6. **Which information creates research insight?** Sector relative strength against IHSG, foreign flow momentum convergence, Regime context.
7. **Which information creates decision advantage?** Brier-score calibrated confidence intervals and strict invalidation criteria preventing emotional holding.
8. **Which information creates learning advantage?** Decomposition of returns (Selection vs. Beta) and explicit Post-Mortems for invalidated theses.
9. **Which information belongs in a Virtual Investment Firm?** Evidence-backed hypotheses, risk boundaries, committee consensus, and signed execution traces.
10. **Which information should be excluded?** Gamified leaderboards, unstructured social commentary, and sub-minute price ticks.

---

## Phase 2: Scope Definition

*   **Market Scope**: IDX ONLY
*   **Currency**: IDR ONLY
*   **Coverage**: IHSG, LQ45, IDX30, Sector Indexes, Individual IDX Stocks.
*   **Exclusions**: US Equities, Crypto, Forex, Commodities, Options, Futures.

**Architectural Challenge**: Does supporting IDX only introduce hard-coded technical debt?
**Justification**: No. The VIF bounded contexts (`Portfolio`, `Thesis`, `CIO`) use opaque `URNs` and `asset_id` strings. We merely constrain the data ingestion providers to IDX universes, keeping the core engines agnostic but the product focused.

---

## Phase 3: Information Architecture

**Objective:** A single-page research workspace avoiding fragmented page hopping.

**Structure:**
The Web Console (Sprint-51 Next.js App) will be extended to include an `IDX Research Terminal` layout utilizing a Master-Detail pane architecture.
*   **Master Sidebar**: Watchlist and Sector filtering.
*   **Detail Pane**: Tabbed workspace containing Overview, Market Data, Research, Thesis, Decision, Outcome, Attribution, Risks.

---

## Phase 4: UX Architecture

### Section A — Market Summary
*   **Purpose**: Immediate macro understanding.
*   **Data**: IHSG change, Market Breadth (Advancers/Decliners), Foreign Net Flow, Total Value.

### Section B — Market Regime
*   **Data**: Classification from Regime Engine (Bull, Bear, Sideways, Volatility score).

### Section C — Stock Discovery
*   **Data**: AG Grid data table for screening LQ45/IDX30 with Foreign Flow and Relative Strength signals.

### Section D — Stock Research Workspace
*   **Tabs**:
    1.  **Overview**: Fundamental metrics (PER, PBV, ROE).
    2.  **Market Data**: Price charts and Foreign Flow as *evidence*.
    3.  **Research**: Bull/Bear case synthesis.
    4.  **Thesis**: Versioned `ThesisDefinition` bindings.
    5.  **Decision**: Linked `CIODecision` and `DecisionJournal` entries.
    6.  **Outcome**: `Performance` tracking (Return, Drawdown).
    7.  **Attribution**: Selection vs Beta contribution.
    8.  **Risks**: Documented `ThesisRisk` factors.

### Section E — Watchlist Command Center
*   Passive monitoring groupings (e.g., "Dividend Yield > 5%").

### Section F — CIO Portfolio Panel
*   Existing Sprint-51 Portfolio Console view.

### Section G — Learning Platform
*   Existing Sprint-51 Investment Oversight view.

---

## Phase 5: Data Provider Architecture

| Data Element | Primary Source | Refresh | Cost | Reliability | Risk |
|---|---|---|---|---|---|
| **IHSG / Indexes** | Yahoo Finance / GoTo | EOD / 15m | Low | Medium | YF API deprecation. |
| **Foreign Flow** | IDX Data / Local Broker APIs | EOD | Medium | High | Data scraping protections. |
| **Broker Summary** | Local Broker APIs | EOD | High | Low | Subject to IDX masking policies. |
| **Fundamentals** | IDN Financials / Yahoo | Quarterly | Medium | High | Delayed reporting. |
| **Corp Actions** | KSEI / IDX Announcements | Daily | Low | High | Parsing complexity. |

*Note: Raw market data will be ingested by a standalone `idx_provider_worker` and published to internal projection caches to insulate the core VIF from third-party unreliability.*

---

## Phase 6: Signal Architecture Review

**Rule:** Raw market data cannot be directly converted into Buy/Sell signals without explainability.

| Classification | Examples | Allowed Usage |
|---|---|---|
| **Evidence** | Foreign Flow, ROE, Sector RS | Read-only input for Analysts. |
| **Research** | Summarized fundamental trajectory | Synthesized narrative. |
| **Thesis** | Bull/Bear versioned hypothesis | Defines invalidation rules. |
| **Decision** | CIO Ledger entry | Signed Authorization. |
| **Outcome** | Drawdown metrics | Triggers invalidation. |
| **Learning** | Post-Mortem | Alters future confidence scaling. |

---

## Phase 7: Backend Architecture

1.  **Executive Summary**: The IDX platform utilizes existing VIF aggregates. A new `PassiveMonitoring` context is introduced for Watchlists. Data ingestion is decoupled via a `Data Abstraction Layer`.
2.  **Ownership Boundary Matrix**:
    *   `MarketData`: Owned by Provider layer.
    *   `Watchlist`: New UI/Passive context.
    *   `Thesis`, `Decision`, `Attribution`: Owned by existing core engines.
3.  **Architecture Overview**: React Frontend $\rightarrow$ API Gateway $\rightarrow$ CQRS Read Projections $\leftarrow$ Event Bus $\leftarrow$ VIF Engines.
4.  **Domain Model**: Leverages `ThesisVersion`, `RegimeSnapshot`, `CIODecision`.
5.  **Aggregate Design**: Strictly immutable, append-only ledgers.
6.  **Value Objects**: `SignalConfidenceScore`, `InvalidationCriteria`.
7.  **Event Contracts**: Adheres to `PortfolioDecisionMadeEvent`, `ThesisVersionActivatedEvent`.
8.  **Application Services**: `IdxIngestionService` (New), `WatchlistService` (New).
9.  **Repositories**: PostgreSQL append-only.
10. **Persistence Design**: Zero mutable aggregates.
11. **API Design**: RESTful over Next.js API routes delegating to Python backend.
12. **Query Design**: Read-side projections built by CDC.
13. **Integration Design**: Asynchronous event bus.
14. **CQRS Design**: Command handlers emit events; Projections serve UI.
15. **Event Journal Design**: Standard Kafka/Redis stream patterns.
16. **Projection Design**: Denormalized `idx_market_summary_projection`.
17. **Sequence Diagrams**: (Available in detailed architecture artifacts).
18. **State Diagrams**: Thesis FSM applies.
19. **Failure Handling**: Stale data defaults to last known good snapshot.
20. **OCC Strategy**: Versioned schema updates on mutable read projections.
21. **Scalability Analysis**: Read-heavy UI served by Redis caches.
22. **Security Analysis**: CIO dual-signature enforcement remains active.
23. **Migration Strategy**: Add IDX projection tables to existing schema.
24. **Risks**: IDX data acquisition stability.
25. **ADR Decisions**: Requires ADR-086 (Watchlist Bounded Context).
26. **Architecture Challenges**: Addressed (e.g., maintaining agnostic core while serving IDX specific UI).
27. **Architecture Delta Analysis**: Small delta. Core remains untouched. UI layer expands.
28. **Acceptance Criteria**: Market data never bypasses Thesis validation.
29. **Final Verdict**: `PENDING_CHALLENGE`

---

## Phase 8: UI Architecture

*   **Framework**: Next.js App Router (Static Export).
*   **Components**: shadcn/ui primitives, AG Grid for Watchlists/Screeners, Tremor for charts.
*   **Page Layout**: Global Sidebar + Main Dashboard + Sliding Details Sheet (shadcn Sheet).
*   **Data Flow**: TanStack Query polling read-side projections.

---

## Phase 9: Roadmap

*   **Wave 1: Market Intelligence** (IDX Data Ingestion Provider, Read Projections).
*   **Wave 2: Stock Discovery** (Watchlist Context, AG Grid UI).
*   **Wave 3: Research Workspace** (Integrate Thesis Engine API).
*   **Wave 4: Thesis Workspace** (Thesis generation UI for IDX stocks).
*   **Wave 5: Decision Workspace** (CIO Dashboard extensions).
*   **Wave 6: Outcome Tracking** (Performance attribution wiring).
*   **Wave 7: Attribution Engine** (Selection/Beta charting).
*   **Wave 8: Learning Platform** (Post-Mortem oversight wiring).

---

## Final Requirement: Challenge Loops

### Challenge Loop 1
*   **Challenge**: Does a "Watchlist" violate the VIF mandate that everything must have a formal thesis?
*   **Response**: A Watchlist is pre-thesis. It is a passive monitoring construct. To protect the `Thesis Engine`, Watchlists must be isolated in a dedicated `PassiveMonitoring` bounded context. They cannot interact with `Capital Allocation` or `CIO`.

### Challenge Loop 2
*   **Challenge**: "Foreign Flow" is requested as a feature. How do we prevent the system from auto-trading based on Foreign Flow?
*   **Response**: Foreign Flow is classified strictly as `RegimeEvidence`. It contributes to the `SignalConfidenceScore` of a Regime or Thesis, but it cannot emit a `Decision` command. The `Execution Engine PEP` will block any trade that lacks a valid `DecisionJournal` reference proving human/agent logical synthesis.

### Verdict
All major architectural risks addressed.

**ARCHITECTURE_FROZEN**
