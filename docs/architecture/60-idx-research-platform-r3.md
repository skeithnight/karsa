# 60. Karsa IDX Research Platform - Architecture Challenge Round 3

**Status:** ARCHITECTURE_REVIEW_ROUND_3

---

## 1. Executive Summary

This document presents the findings of the third architecture challenge round for the Karsa IDX Research Platform. The goal was to aggressively validate whether the architecture embodies an institutional Virtual Investment Firm or regresses into a retail stock screener. 

By aggressively dismantling earlier assumptions regarding Watchlist domains, simplistic Regimes, and "black box" jumps from Market Data to Thesis, this review enforces the introduction of the **Market Structure Engine**, the **Analyst Execution Layer**, and the **Forecast Engine**. This completely reframes the architecture into a rigorous, accountable investment lifecycle capable of sustaining ex-post attribution.

---

## 2. Architecture Delta Analysis

| Area | Previous Architecture (Sprint-59) | Revised Architecture (Round 3) | Justification |
|---|---|---|---|
| **Watchlist** | `PassiveMonitoring` Bounded Context | **User Preference Ownership** | Watchlists have no domain logic or transactions. |
| **Market Data** | Direct feed to Research | **Intercepted by Market Structure Engine** | Raw data is noise. Institutional insights require structure (Breadth, Rotation). |
| **Research Synthesis** | Monolithic AI parsing | **Analyst Worker Layer** | Enforces structured consensus and multi-disciplinary synthesis. |
| **Forecasting** | Implicit in Thesis | **First-Class Forecast Engine** | Enables explicit ex-post Brier scoring and probabilistic accountability. |
| **Regimes** | Bull / Bear / Sideways | **Hierarchical Expansion/Exhaustion States** | Captures true market mechanics and liquidity cycles. |
| **Providers** | Ad-hoc scrapers & APIs | **First-Class Provider Platform** | Mitigates the highest production risk (bad data). |
| **UX** | Single-Page Terminal | **Role-Based Workspaces** (Market, Stock, Portfolio, Learning) | Prevents cognitive overload and respects VIF workflow separation. |

---

## 3. Ownership Boundary Matrix

| Stage / Component | Owner Context | Permitted Action |
|---|---|---|
| **Raw Market Data Collection** | Provider Platform | Fetch, Validate, Publish |
| **Market Breadth & Sector Rotation** | Market Structure Engine | Analyze, Aggregate, Emit Snapshot |
| **User Stock Lists** | UI / User Preference | Render UI (No Domain Logic) |
| **Multi-Disciplinary Synthesis** | Analyst Layer (Execution) | Produce `AnalystReport` |
| **Confidence & Probability Calculation**| Forecast Engine | Generate `ForecastRecord` |
| **Hypothesis & Risk Definitions** | Thesis Engine | Draft, Approve, Invalidate |
| **Review & Accountability** | Post-Mortem & Review Engine | Audit, Ex-Post Attribution |

---

## 4. Domain Model Updates

*   **ProviderRegistry**: Tracks provider health, scoring, and failovers.
*   **MarketStructureSnapshot**: Aggregates breadth, rotation, and liquidity observations.
*   **AnalystReport**: Worker-specific evaluation output (e.g., `RegimeAnalystReport`).
*   **ForecastRecord**: Explicit declaration of expected return and probability, mapped 1:1 to a `ThesisVersion`.

---

## 5. Event Contract Updates

*   `ProviderDataStaleEvent`: Emitted when heartbeat SLA fails. Triggers failover.
*   `MarketStructureShiftEvent`: Emitted on major liquidity or breadth divergence.
*   `ForecastGeneratedEvent`: Emitted when a forecast is sealed. Contains `ExpectedReturn` and `SuccessProbability`.
*   `RegimeStateTransitionEvent`: Emitted when the hierarchical regime taxonomy officially pivots (e.g., Bull Expansion $\to$ Bull Exhaustion).

---

## 6. Forecast Architecture

The `Forecast Engine` formalizes expected outcomes, bridging Research and Thesis.
*   **Ownership**: Forecast Engine.
*   **Immutability**: Strictly immutable (`write-once`) upon sealing.
*   **Versioning**: Linked 1:1 with `ThesisVersion`. A change in forecast requires a new thesis version.
*   **Outcome Evaluation**: `Performance Engine` uses it ex-post to calculate Brier Scores.
*   **Attribution**: Provides the ex-ante baseline for Expected Return vs. Expected Drawdown, feeding the `Attribution Engine`.

**Forecast Aggregate:**
*   `Expected Return`
*   `Expected Drawdown`
*   `Expected Volatility`
*   `Success Probability`
*   `Risk/Reward Ratio`
*   `Time Horizon`

---

## 7. Market Structure Architecture

The `Market Structure Engine` sits between raw Market Data and Research.
*   **Market Data**: Raw ticks, OHLCV, raw foreign flow.
*   **Market Structure**: Sector Rotation, Market Breadth, Relative Strength, Liquidity Expansion/Contraction, Broker Accumulation.
*   **Research**: The narrative synthesis of the Market Structure.
*   **Thesis**: Formalized investment rule.

**Acceptance Criteria**: Research Engine must consume `MarketStructureSnapshot`s and cannot directly query raw price ticks.

---

## 8. Analyst Architecture

The `Analyst Execution Layer` structures the "black box" jump from data to thesis.
*   **Nature**: Analysts are specialized execution workers producing `AnalystReport`s, not bounded contexts.
*   **Roles**: Regime Analyst, Fundamental Analyst, Technical Analyst, Foreign Flow Analyst, Sector Rotation Analyst, Dividend Analyst, Risk Analyst.
*   **Conflict Resolution**: A `LeadAnalyst` worker acts as the consensus layer, identifying conflicting reports and generating a synthesized `ResearchRun` that highlights the discrepancies.

---

## 9. Provider Platform Architecture

The `Provider Platform` acts as a first-class Anti-Corruption Layer (ACL).
*   **Components**: Provider Registry, Provider Health Monitoring, Data Quality Scoring, Capability Registry.
*   **Categories**: Market Data, Fundamental, Corporate Action, Foreign Flow, Broker Summary, Macro.
*   **Disagreements**: Resolved via `DataQualityScoring` (consensus voting or primary/secondary precedence).
*   **Failures**: Automated routing to secondary providers in the `ProviderRegistry`.
*   **Stale Detection**: Enforced delivery SLAs (Heartbeats).

---

## 10. UX Architecture Recommendation

**Verdict: Option C (Market Workspace + Stock Workspace + Portfolio Workspace + Learning Workspace)**

A Single-Page Terminal creates unmanageable cognitive load. Separating the UX into four distinct role-based workspaces mirrors the backend contexts and institutional workflows perfectly:
1.  **Market Workspace**: Market Structure, Regime, Breadth.
2.  **Stock Workspace**: Watchlist preferences, Analyst Reports, Forecasts, Theses.
3.  **Portfolio Workspace**: CIO Engine limits, Execution, Capital Allocation.
4.  **Learning Workspace**: Review, Post-Mortems, Attribution breakdowns.

---

## 11. Risks

*   **Latency in Pipeline**: Introducing Market Structure, Analysts, and Forecasts serializes hypothesis generation, increasing latency.
    *   *Mitigation*: As an institutional Virtual Investment Firm, accuracy and explainability supersede high-frequency execution speed.
*   **Provider Redundancy Cost**: Running multiple IDX data providers for failover incurs high API costs.
    *   *Mitigation*: Implement aggressive caching in the Provider Platform and scale polling rates dynamically based on the current `RegimeSnapshot`.

---

## 12. ADR Recommendations

*   **ADR-086**: Deprecate Watchlist as a Bounded Context; formalize as a UI User Preference.
*   **ADR-087**: Establish Market Structure Engine as the mandatory intermediary between Providers and Research.
*   **ADR-088**: Establish Forecast Engine to own probabilistic ex-ante outcomes for ex-post Brier scoring.
*   **ADR-089**: Upgrade Regime Engine to a Hierarchical Expansion/Exhaustion Taxonomy.
*   **ADR-090**: Establish the Analyst Execution Layer as the research synthesis coordinator.

---

## 13. Acceptance Criteria

1.  **Watchlist Independence**: Watchlists emit no domain events and own no backend aggregates.
2.  **Market Structure Constraint**: Research Runs fail validation if they attempt to bypass the `MarketStructureSnapshot`.
3.  **Forecast Lineage**: Every `ThesisVersion` strictly references one `ForecastRecord`.
4.  **Analyst Consensus**: A `ResearchRun` must contain attached evidence of multi-analyst consensus or documented conflict.
5.  **Provider Failover**: A simulated provider heartbeat failure successfully redirects queries to the fallback provider without breaking downstream projections.

---

## 14. Freeze Readiness Assessment

The architecture has survived aggressive challenge loops.
*   Retail "Screener" behaviors (Watchlist contexts) have been eradicated.
*   Black box jumps have been eliminated via Market Structure, Analyst, and Forecast engines.
*   The Provider Platform effectively insulates the CQRS core from the high-risk reality of external IDX APIs.
*   The design is fully compatible with Karsa's existing immutable, write-once ledger requirements and ex-post learning loops.

All strategic gaps are closed.

---

## 15. Final Verdict

**ARCHITECTURE_FROZEN**
