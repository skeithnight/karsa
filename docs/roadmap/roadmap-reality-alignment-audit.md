# Roadmap Reality Alignment Audit Report

This report presents a comprehensive repository-wide capability inventory and alignment audit, comparing Karsa's current implementation reality with the consolidated roadmap and the target Virtual Investment Firm (VIF) architecture.

---

## 1. Repository Capability Inventory

The following table inventories the actual implementation state of all 19 VIF bounded contexts in `src/karsa/**`:

| Bounded Context | Status | Description |
| :--- | :--- | :--- |
| **Capability Engine** | `IMPLEMENTED` | Complete domain model, validation logic, and services in [capabilities](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/capabilities). Utilizes file-based and in-memory repositories. |
| **Provider Abstraction** | `IMPLEMENTED` | Routing, bindings, and provider registry services in [providers](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/providers). Utilizes file-based and in-memory repositories. |
| **Capability Registry** | `IMPLEMENTED` | Operational via the `CapabilityRegistryService` in [services.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/capabilities/application/services.py#L108-L200) within the capabilities context. |
| **Observability** | `PRODUCTION_READY` | Highly structured tracing and metrics, including spans, kinds, collector aggregations, and retention tiers in [observability](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/observability). |
| **Attribution** | `PRODUCTION_READY` | PostgreSQL-backed lineage tracking, restatements, and input projections in [attribution](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution). |
| **Governance** | `PRODUCTION_READY` | Policy enforcement, PDP/PEP validation boundaries, exception tokens, and governance budget caching in [governance](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/governance). |
| **Allocation** | `PRODUCTION_READY` | PostgreSQL-backed capital allocation, solver optimizations, and weight recommendations in [allocation](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/allocation). |
| **Review** | `PRODUCTION_READY` | Session lifecycle, qualitative review forms, learning loops, and event replay projections in [review](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/review). |
| **Thesis** | `IMPLEMENTED` | PostgreSQL-backed state machine (Draft, Proposed, Active, Invalidated, Realized) in [thesis](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis). Contains broken legacy repository files to clean up. |
| **Performance** | `IMPLEMENTED` | Fully operational returns, Brier score, Sharpe, drawdown, and hit-rate calculations in [performance](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/performance). Currently uses file-based JSON storage. |
| **Portfolio** | `PRODUCTION_READY` | PostgreSQL-backed authoritative Real-Time Book Of Record (RTBOR), cash/position ledgers, and valuations in [portfolio](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio). |
| **Execution** | `PRODUCTION_READY` | Authoritative transactional edge, order/fill routing, interactive broker adapters, and PEP dual-signature checks in [execution](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/execution). |
| **CIO** | `NOT_PRESENT` | No source directory or files exist. |
| **Decision Journal** | `NOT_PRESENT` | No source directory or files exist. |
| **Post-Mortem** | `NOT_PRESENT` | No source directory or files exist. |
| **Research** | `NOT_PRESENT` | No source directory or files exist. |
| **Regime** | `NOT_PRESENT` | No source directory or files exist. |
| **Knowledge Graph** | `NOT_PRESENT` | No source directory or files exist. |
| **Risk** | `NOT_PRESENT` | No source directory or files exist. |

---

## 2. Roadmap Alignment Matrix

| Context / Aspect | Roadmap Status | Repository Reality | Alignment Finding |
| :--- | :--- | :--- | :--- |
| **Performance Engine** | Scheduled for future evolution | Already implemented (~75% complete) | **Implementation ahead of roadmap**. Sprints should be rescoped to focus on database evolution rather than greenfield design. |
| **Thesis Engine** | Scheduled for future evolution | Already implemented (~80% complete) | **Implementation ahead of roadmap**. Core aggregate and postgres mapper exist; sprint must focus on refactoring legacy repository debt. |
| **CIO Engine** | Marked as Completed/Closed (Design Only) | **NOT_PRESENT** | **Roadmap Gap / Drift**. Complete gap; no implementation sprint has been scheduled for this critical control-plane context. |
| **Decision Journal** | Marked as Completed/Closed (Design Only) | **NOT_PRESENT** | **Roadmap Gap / Drift**. Complete gap; no implementation sprint has been scheduled to realize hindsight-prevention ledgers. |
| **Post-Mortem Engine** | Marked as Completed/Closed (Design Only) | **NOT_PRESENT** | **Roadmap Gap / Drift**. Complete gap; no implementation sprint has been scheduled for the failure taxonomy/feedback loop. |
| **Risk Engine** | Scheduled for Sprint-37 | **NOT_PRESENT** | **Aligned**. Appropriately scheduled in the future per the findings of [23-vif-master-delta-analysis.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/23-vif-master-delta-analysis.md). |
| **Research Engine** | Scheduled for Sprint-38 | **NOT_PRESENT** | **Aligned**. Scheduled in the future. |
| **Regime Engine** | Scheduled for Sprint-40 | **NOT_PRESENT** | **Aligned**. Scheduled in the future. |
| **Knowledge Graph** | Scheduled for Sprint-41 | **NOT_PRESENT** | **Aligned**. Scheduled in the future. |

---

## 3. Reuse vs Replace Analysis

For future sprints, we classify the work required as follows:

1. **Sprint-36: Performance Engine Evolution**
   - **Classification**: `EVOLUTION`
   - **Rationale**: Reuse the existing, well-tested ex-post calculations (Brier, Sharpe, hit rates) from [performance](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/performance). Evolve the persistence layer from file JSON to PostgreSQL, add Sortino calculations, and expose REST presentation routes.
2. **Sprint-37: Risk Engine Foundation**
   - **Classification**: `GREENFIELD`
   - **Rationale**: There is zero existing code. Build the dedicated, forward-looking ex-ante Risk Engine (VaR, expected shortfall, stress testing, covariance forecasts) from scratch to support Capital Allocation solvers and Governance PEP checks.
3. **Sprint-38: Thesis Engine Evolution**
   - **Classification**: `EVOLUTION` / `REFACTOR`
   - **Rationale**: Reuse the existing `Thesis` aggregate state machine and psycopg mappings. Remove the broken legacy files, integrate the postgres repository, and connect outbox event streams.
4. **Sprint-39: Decision Journal Foundation**
   - **Classification**: `GREENFIELD`
   - **Rationale**: Build the pre-outcome reasoning ledger from scratch per [18-decision-journal.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/18-decision-journal.md).
5. **Sprint-40: CIO Engine Foundation**
   - **Classification**: `GREENFIELD`
   - **Rationale**: Build the authoritative investment committee and decision authorization ledger from scratch per [22-cio-engine.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/22-cio-engine.md).
6. **Sprint-41: Post-Mortem Engine Foundation**
   - **Classification**: `GREENFIELD`
   - **Rationale**: Build the failure classification taxonomy and feedback mapping ledger from scratch per [19-post-mortem-engine.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/19-post-mortem-engine.md).
7. **Sprint-42: Research Engine Foundation**
   - **Classification**: `GREENFIELD`
   - **Rationale**: Build the signals and data provenance sandbox from scratch.
8. **Sprint-43: Regime Engine Foundation**
   - **Classification**: `GREENFIELD`
   - **Rationale**: Build the macro classification and volatility state classifier.
9. **Sprint-44: Knowledge Graph Foundation**
   - **Classification**: `GREENFIELD`
   - **Rationale**: Build the semantic querying and business memory storage layer.

---

## 4. Future Sprint Reassessment

* **Sprint-36 (Performance Engine Evolution)**: **Should remain**. The Performance Engine is currently in `IMPLEMENTED` state using local JSON file storage. It must be evolved to use PostgreSQL tables, add Sortino metrics, and establish runtime API endpoints.
* **Sprint-37 (Risk Engine Foundation)**: **Should remain**. The context does not exist. A dedicated Risk Engine is mathematically distinct from Portfolio/Performance (ex-ante predictive distributions vs transactional holdings or ex-post facts) per [ADR-049-risk-ownership.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-049-risk-ownership.md) and must be built greenfield.
* **Sprint-38 (Thesis Engine Evolution)**: **Should remain (but renumbered/rescoped)**. While the thesis model and database mappings exist, the context contains broken repository files and must be evolved/refactored.
* **Sprint-39 (Decision Journal Foundation / Evolution)**: **Should remain (but re-scheduled as a Greenfield implementation)**. This context was previously designed but not implemented.

---

## 5. Architecture Delta Analysis

The exact gaps between the current repository reality and the VIF target architecture are:

1. **Missing Control-Plane Contexts**:
   - **Decision Journal**: Lacks immutable ledger writes for pre-outcome reasoning, hindering hindsight-contamination prevention.
   - **Post-Mortem**: Lacks failure taxonomy classification and weighted root-cause feedback loops.
   - **CIO**: Lacks authoritative orchestration of strategy trees, promotion/retirement commands, and cryptographically signed decision authorization ledger.
2. **Missing Analytics-Plane Contexts**:
   - **Risk**: Lacks ex-ante VaR, Expected Shortfall, stress testing scenarios, and covariance matrix calculations.
   - **Research**: Lacks signal registries and prompt/dataset lineage auditing.
   - **Regime**: Lacks macro market-regime state classifiers.
   - **Knowledge Graph**: Lacks semantic queries mapping connections between theses, strategies, decisions, and outcomes.
3. **Database Integration Gaps**:
   - Capabilities, Providers, Observability, Governance, Execution, and Performance contexts still persist their states in JSON files or in-memory repositories instead of PostgreSQL schemas.

---

## 6. Remaining Missing Bounded Contexts

The following bounded contexts are completely missing from the codebase:

1. **CIO Engine** (`src/karsa/cio` is missing)
2. **Decision Journal** (`src/karsa/decision_journal` is missing)
3. **Post-Mortem Engine** (`src/karsa/post_mortem` is missing)
4. **Risk Engine** (`src/karsa/risk` is missing)
5. **Research Engine** (`src/karsa/research` is missing)
6. **Regime Engine** (`src/karsa/regime` is missing)
7. **Knowledge Graph** (`src/karsa/knowledge_graph` is missing)

---

## 7. Technical Debt Inventory

* **Legacy Modules / Broken Repository Files**:
  - [postgres_thesis_repository.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/infrastructure/storage/postgres_thesis_repository.py) and [in_memory_thesis_repository.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/infrastructure/storage/in_memory_thesis_repository.py) import the non-existent class `ActiveThesis` from the thesis domain models, causing errors if imported.
* **Duplicate Repositories**:
  - [thesis_repository.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/domain/repository/thesis_repository.py) is a duplicate and broken repository interface that imports `ActiveThesis`, whereas [thesis_repository.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/thesis/infrastructure/storage/thesis_repository.py) is the clean, correct Postgres repository implementation.
* **Deprecated Paths**:
  - The root-level test suite files [test_artifacts.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/test_artifacts.py), [test_state_tracking.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/test_state_tracking.py), and [test_workflow.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/test_workflow.py) fail because they reference obsolete modules (`karsa.artifacts.manager` and `karsa.workflow.controller`).
* **Obsolete Sprint Assumptions**:
  - The dashboard assumes that Sprints 18, 20, 22, 24, 25 resolved the implementation of their respective engines, failing to account for the fact that Decision Journal, Post-Mortem, and CIO were designed but never implemented.

---

## 8. Final Recommended Roadmap

To align the roadmap with the actual repository state and fill the missing control-plane gaps, we propose the following revised roadmap:

* **Sprint-36**: Performance Engine Evolution (Evolve local JSON file storage to PostgreSQL, implement Sortino ratio, expose REST endpoints).
* **Sprint-37**: Risk Engine Foundation (Dedicated ex-ante Risk Engine per [ADR-049-risk-ownership.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-049-risk-ownership.md)).
* **Sprint-38**: Thesis Engine Evolution (Refactor duplicate and broken repositories, clean up `ActiveThesis` references, finalize migrations).
* **Sprint-39**: Decision Journal Foundation (Implement immutable pre-outcome reasoning ledger per [18-decision-journal.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/18-decision-journal.md)).
* **Sprint-40**: CIO Engine Foundation (Implement write-once CIO decision ledger and authorization flows per [22-cio-engine.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/22-cio-engine.md)).
* **Sprint-41**: Post-Mortem Engine Foundation (Implement failure analysis and failure taxonomy ledger per [19-post-mortem-engine.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/19-post-mortem-engine.md)).
* **Sprint-42**: Research Engine Foundation (Implement signal sandbox and prompt auditing).
* **Sprint-43**: Regime Engine Foundation (Implement market regime classification).
* **Sprint-44**: Knowledge Graph Foundation (Implement semantic query and storage layer).

---

## 9. Final Verdict

### **ROADMAP_RESCOPE_REQUIRED**
