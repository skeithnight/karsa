# 27. Virtual Investment Firm Master Architecture Delta Audit

This report presents a repository-wide architectural delta audit comparing Karsa's current implemented platform (post-Sprint-40 closed) against the target Virtual Investment Firm (VIF) reference architecture.

---

## 1. Executive Summary

A repository-wide architecture audit was performed on the Karsa codebase following the closure of Sprint-40 (Risk Engine Foundation). The objective was to validate the integration state, mapping of bounded contexts, event flows, governance/observability controls, and evaluate the upcoming sprints on the roadmap.

The audit confirms that the core transactional engines (Decision Journal, CIO, Execution, Portfolio, Risk, and Post-Mortem) are functionally complete and implement VIF-standard patterns (write-once immutable aggregates, range-partitioned tables, database trigger protection, and event versioning). However, several critical gaps remain:
1. **Legacy Debt**: The Thesis Engine (Sprint-13/23 design) lacks modern VIF constraints, partitioning, and immutability triggers.
2. **Upstream Isolation**: The Research Engine is missing, leaving signal templates and provenance disconnected from the investment lifecycle.
3. **Stubs & Mocks**: The Regime Engine is missing (simulated via fallbacks in the Risk Engine), and pre-trade PEP limit exceptions and Brier score outcome calculations utilize simulated inputs or test fixtures.

To resolve legacy debt and complete the upstream investment loop, the current roadmap sequence is validated. **Sprint-41: Thesis Engine Evolution** is the highest-leverage next step.

**Audit Verdict**: `ROADMAP_VALIDATED`

---

## 2. Current State Architecture Map

The VIF platform consists of 9 active bounded contexts, outlined below:

### Thesis Engine
* **Purpose**: Manages investment hypotheses, parameter constraints, version hashes, and active thesis bindings.
* **Aggregate Roots**: `Thesis`
* **Ownership Boundaries**: Authoritative owner of qualitative hypotheses and thesis parameters.
* **Integration Points**: Decision Journal URN references and Review Engine.
* **Implementation Status**: *Partially Implemented* (Legacy design patterns, missing VIF trigger-based immutability, range partitioning, and updated event schemas).

### Decision Journal
* **Purpose**: Captures pre-outcome reasoning, decision snapshots, confidence values, and correction chains to prevent hindsight bias.
* **Aggregate Roots**: `DecisionRecord`
* **Ownership Boundaries**: Authoritative owner of pre-trade investment rationale and expectations.
* **Integration Points**: Upstream Thesis URNs, downstream CIO decisions, and Performance Engine calibrations.
* **Implementation Status**: *Fully Implemented* (Postgres-backed, range partitioned, trigger-protected, event versioned).

### CIO Engine
* **Purpose**: Manages the strategic portfolio target configuration tree, committee decision logs, and pre-trade authorization signatures.
* **Aggregate Roots**: `CIODecision`
* **Ownership Boundaries**: Authoritative owner of portfolio targets and trade authorization signatures.
* **Integration Points**: Execution PEP validations and Decision Journal URNs.
* **Implementation Status**: *Fully Implemented* (Postgres-backed, cryptographic Ed25519 signatures, trigger-protected).

### Execution Engine
* **Purpose**: Stages orders, runs Policy Enforcement Point (PEP) limit checks, routes trades to broker adapters, and indexes fill records.
* **Aggregate Roots**: `OrderBook`, `FillRecord`
* **Ownership Boundaries**: Authoritative owner of broker order routing and transaction fills.
* **Integration Points**: Downstream Portfolio Engine (via fills), upstream CIO Engine (signatures), and Governance (exception tokens).
* **Implementation Status**: *Fully Implemented* (Postgres-backed, PEP limit checks, write-once ledgers).

### Portfolio Engine
* **Purpose**: Tracks real-time position books, cash balances, cash transactions, and asset valuations.
* **Aggregate Roots**: `PositionBook`
* **Ownership Boundaries**: Authoritative owner of current positions, cash books, and valuations.
* **Integration Points**: Upstream Execution fills, downstream Performance and Risk engines (exposures and valuation snapshots).
* **Implementation Status**: *Fully Implemented* (Postgres-backed, Real-Time Book of Record (RTBOR)).

### Performance Engine
* **Purpose**: Evaluates ex-post historical returns, Sharpe ratios, Sortino ratios, and drawdowns.
* **Aggregate Roots**: `PerformanceRecord`
* **Ownership Boundaries**: Authoritative owner of historical outcomes.
* **Integration Points**: Upstream Portfolio snapshots, downstream Risk Engine (for return volatility input).
* **Implementation Status**: *Fully Implemented* (Postgres-backed, ex-post returns analysis).

### Review Engine
* **Purpose**: Evaluates signal convergence qualitatively.
* **Aggregate Roots**: `ReviewRecord`
* **Ownership Boundaries**: Authoritative owner of qualitative performance convergence reviews.
* **Integration Points**: Integrates with raw text logs and decision records.
* **Implementation Status**: *Partially Implemented* (text parsing based, lacks robust DB connection).

### Post-Mortem Engine
* **Purpose**: Conducts failure classification, root-cause weight attributions, and ex-post action-item recommendations.
* **Aggregate Roots**: `PostMortemRecord`, `Recommendation`
* **Ownership Boundaries**: Authoritative owner of post-incident evaluations and recommendations.
* **Integration Points**: Reads Decision Journal, Performance records, and Portfolio snapshots; outputs action-item recommendations.
* **Implementation Status**: *Fully Implemented* (Postgres-backed, state machine lifecycle, OCC concurrency, history logs).

### Risk Engine
* **Purpose**: Calculates forward-looking ex-ante portfolio risk metrics.
* **Aggregate Roots**: `RiskEvaluationRecord` (append-only), `CovarianceForecast`, `StressEvaluationRecord`.
* **Ownership Boundaries**: Authoritative owner of portfolio risk metrics and covariance forecasts.
* **Integration Points**: Reads Portfolio holdings snapshots and historical return data; outputs metrics to Governance and Capital Allocation.
* **Implementation Status**: *Fully Implemented* (Postgres-backed, range partitioned, triggers block mutations).

---

## 3. Existing Bounded Context Matrix

| Context | Status | Owner Responsibilities | Aggregate Roots | Key Events | Dependencies |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Thesis Engine** | Partially Implemented (Legacy) | Hypotheses & parameters definition | `Thesis` | `ThesisCreated` | None |
| **Decision Journal** | Fully Implemented | Pre-outcome rationale & confidence logs | `DecisionRecord` | `DecisionRecorded` | Thesis URN |
| **CIO Engine** | Fully Implemented | Portfolio targets & trade authorization | `CIODecision` | `CIODecisionApproved` | Decision Journal URN |
| **Execution Engine** | Fully Implemented | Order routing, fills indexing & PEP | `OrderBook`, `FillRecord` | `OrderStaged`, `OrderFilled` | CIO, Governance, Portfolio |
| **Portfolio Engine** | Fully Implemented | Position books & cash ledger tracking | `PositionBook` | `PositionUpdated`, `CashTransactionRecorded` | Execution Fills |
| **Performance Engine** | Fully Implemented | Ex-post return & Sharpe analysis | `PerformanceRecord` | `PerformanceEvaluated` | Portfolio holdings snapshots |
| **Review Engine** | Partially Implemented | Qualitative signal convergence reviews | `ReviewRecord` | `ReviewCompleted` | Text files, Decisions |
| **Post-Mortem Engine** | Fully Implemented | Root-cause analysis & ex-post recommendations | `PostMortemRecord`, `Recommendation` | `PostMortemRecordCreated`, `RecommendationCreated` | CIO, Performance, Risk, Portfolio |
| **Risk Engine** | Fully Implemented | Ex-ante VaR/CVaR, covariance & stress analysis | `RiskEvaluationRecord`, `CovarianceForecast`, `StressEvaluationRecord` | `RiskEvaluationCreated`, `CovarianceForecastUpdated` | Portfolio snapshot, Regime multiplier |

---

## 4. Missing Bounded Context Analysis

To satisfy the target VIF reference architecture, the following bounded contexts must be introduced:

### Research Engine
* **Why it exists**: Manages raw data signals, prompt templates, signal sandboxes, and data provenance.
* **Dependencies**: None.
* **Business Value**: Establishes data lineage from raw signals to thesis generation.
* **Implementation Complexity**: Medium-High (requires signal sandboxing and sandbox testing logic).
* **Production Criticality**: High (essential to automate and audit AI agent generation of theses).

### Regime Engine
* **Why it exists**: Classifies macro volatility regimes and states.
* **Dependencies**: Performance Engine (historical returns).
* **Business Value**: Adjusts risk calculations based on structural market changes.
* **Implementation Complexity**: Medium (regime classification algorithms).
* **Production Criticality**: High (replaces the current static neutral fallback multiplier in the Risk Engine).

### Knowledge Graph Platform
* **Why it exists**: Maps semantic relationships and provenance across the entire investment lifecycle.
* **Dependencies**: All transactional engines (Thesis, Decision, CIO, Execution, Portfolio, Performance, Risk, Review, Post-Mortem).
* **Business Value**: Allows AI agents and auditors to query semantic connections.
* **Implementation Complexity**: High (requires graph database integration and metadata mapping).
* **Production Criticality**: Medium (highly valuable for auditability and AI-agent compatibility, but doesn't block transactional order routing).

---

## 5. Missing Platform Service Analysis

The target architecture requires the following platform services:
1. **Regime Engine Service**: Computes macro classifications and publishes regime states.
2. **Attribution Platform Service**: Computes fine-grained ex-post attribution (separating thesis, execution, and allocation alpha).
3. **Observability Platform Service**: Aggregates traces, worker logs, and decision lineage across all distributed contexts.
4. **Knowledge Graph Platform Service**: Manages metadata schemas, triples, and semantic query execution.
5. **Capital Allocation Solver Service**: Executes risk-budgeting optimizations and mean-variance calculations.

---

## 6. Missing Event Flow Analysis

The following event-driven integrations are missing:
* **Regime Engine $\rightarrow$ Risk Engine**: `RegimeChangedEvent` $\rightarrow$ triggers recalculation of volatility forecasts with new multipliers.
* **Research Engine $\rightarrow$ Thesis Engine**: `SignalValidatedEvent` $\rightarrow$ triggers creation of a new investment thesis.
* **Capital Allocation $\rightarrow$ CIO Engine**: `TargetAllocationOptimizedEvent` $\rightarrow$ triggers CIO decision tree updates.
* **Attribution Engine $\rightarrow$ Review/Post-Mortem**: `AlphaDecayDetectedEvent` $\rightarrow$ triggers qualitative reviews.

---

## 7. Missing Registry Analysis

To support capability-based security and dynamic workflows, the VIF requires:
* **Model Registry**: Tracks active mathematical forecasts, backtest parameters, and model versions.
* **Regime Registry**: Tracks historical macro states and active regime definitions.
* **Policy Registry**: Stores active compliance constraints used by the PDP/PEP.
* **Attribution Registry**: Tracks attribution calculations for active capital allocations.
* **Capability Registry**: Maps which AI agents own which capabilities across the VIF.

---

## 8. Governance Gap Analysis

* **PDP (Policy Decision Point)**: The PDP evaluates rules, but exception workflows are not fully integrated via signed tokens.
* **PEP (Policy Enforcement Point)**: Verifications are currently stubbed/mocked in execution.
* **Policy Lifecycle**: Lacks an automated workflow from draft to retired states in the production database.
* **Auditability**: Complete for implemented aggregates, but missing for untracked policy edits and exceptions.

---

## 9. Observability Gap Analysis

* **Traces & Metrics**: Basic trace objects exist in `shared/infrastructure`, but lack OpenTelemetry integration.
* **Decision Lineage**: Fully trackable through URN strings across Decision -> CIO -> Execution -> Portfolio, but requires a Knowledge Graph to map semantically.
* **Worker/Agent Visibility**: Prototyped but disconnected from active execution loops.

---

## 10. Attribution Gap Analysis

* **Thesis Attribution**: Missing. Cannot distinguish whether portfolio returns are due to thesis accuracy or execution alpha.
* **Execution Attribution**: Missing. Slippage and market impact are not computed.
* **Regime Attribution**: Missing. Cannot separate regime-induced returns from asset selection alpha.
* **Allocation Attribution**: Missing. Cannot attribute performance to target-weight changes versus security selection.

---

## 11. Performance Gap Analysis

* **Calibration & Confidence Scoring**: Decision Journal logs confidence values, but Performance Engine does not read them for Brier score outcomes (relies on mock inputs).
* **Ranking & Benchmarking**: Lacks multi-horizon relative ranking of active theses.

---

## 12. Architecture Delta Analysis

* **Fully Implemented**: Decision Journal, CIO Engine, Execution Engine, Portfolio Engine, Post-Mortem Engine, Risk Engine.
* **Partially Implemented**: Thesis Engine (legacy code, needs evolution), Performance Engine (basic ex-post calculations, lacks calibration integration), Review Engine (basic text-based reviews), Governance (evaluators exist but PEP is mocked).
* **Missing**: Research Engine, Regime Engine, Capital Allocation Engine, Attribution Engine.
* **Future Evolution**: Knowledge Graph, Multi-agent coordination layers.

---

## 13. Critical Path Analysis

* **Production Readiness**: Blocked by legacy Thesis Engine code and simulated Governance exceptions.
* **Learning-loop Completion**: Blocked by missing Research Engine and lack of integration between Performance Brier scores and Decision Journal confidence parameters.
* **Governance Maturity**: Blocked by stubbed PDP exception tokens.

---

## 14. Recommended Sprint Order

1. **Sprint-41: Thesis Engine Evolution**
   - *Objective*: Modernize Thesis Engine database repositories, standardize aggregates to extend `ImmutableAggregate`, and clean up `ActiveThesis` state mutations.
   - *Dependencies*: None.
   - *Expected Value*: Resolves technical debt and provides a clean, VIF-standard foundation.
   - *Risk Reduction*: Eliminates legacy schema inconsistencies.
2. **Sprint-42: Research Engine Foundation**
   - *Objective*: Implement signal sandbox and template auditing.
   - *Dependencies*: Thesis Engine (modernized).
   - *Expected Value*: Completes signal provenance.
   - *Risk Reduction*: Prevents untracked signal injections.
3. **Sprint-43: Regime Engine Foundation**
   - *Objective*: Implement regime classification and active multipliers.
   - *Dependencies*: Performance Engine (historical returns).
   - *Expected Value*: Replaces mock volatility fallbacks.
   - *Risk Reduction*: Reduces volatility forecasting error during market stress.
4. **Sprint-44: Knowledge Graph Foundation**
   - *Objective*: Implement semantic query and relationship storage.
   - *Dependencies*: All core transactional contexts.
   - *Expected Value*: Integrates metadata and audits.
   - *Risk Reduction*: Simplifies lineage verification.

---

## 15. Roadmap Validation

* **Is the roadmap sequence still valid?**: Yes.
* **Should priorities be reordered?**: No, the current sequence is highly logical and handles upstream dependencies (Thesis -> Research) before downstream enhancements (Regime -> Knowledge Graph).
* **What is the highest leverage next sprint?**: Sprint-41: Thesis Engine Evolution, as it resolves foundational legacy debt.

---

## 16. Risks

* **Legacy Code Coupling**: Legacy Thesis structures could cause integration failures with new Research signal models.
* **Data Integrity**: Delaying Regime Engine forces prolonged reliance on default constants.

---

## 17. Acceptance Criteria for Sprint-41

1. **Standardized Aggregate**: Thesis aggregate must extend `ImmutableAggregate` and prevent updates/deletes.
2. **Database Schema**: Postgres table schema for `theses` must be range-partitioned and migration-backed.
3. **Immutability Triggers**: Alembic migration must create triggers to block UPDATE/DELETE queries on database tables.

---

## 18. Final Verdict

### **ROADMAP_VALIDATED**
