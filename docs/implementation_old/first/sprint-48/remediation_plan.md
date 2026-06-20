# Sprint-48 Remediation Plan (Revised)

## 1. Remediation Coverage Matrix
| Audit Finding | Description | Remediating Work Package | Status |
|---------------|-------------|--------------------------|--------|
| F-01 | Repositories use `pass` | WP-1 (Database Integrity) | Mapped |
| F-02 | Migrations use `pass` | WP-1 (Database Integrity) | Mapped |
| F-03 | Projections use `pass` | WP-5 (CQRS & Self-Learning Projections) | Mapped |
| F-04 | Attribution hardcodes math | WP-3 (Attribution Math) | Mapped |
| F-05 | Performance missing Regime | WP-2 (Performance Engine Completion) | Mapped |
| F-06 | Testing lacks behavior | WP-6 (Behavioral Integration Testing) | Mapped |
| F-07 | Trust score OCC missing | WP-1 (Database Integrity) | Mapped |
| F-08 | Missing Journal -> Decision | WP-4 (End-to-End Workflow Edges) | Mapped |
| F-09 | Self-Learning event-only | WP-5 (CQRS & Self-Learning Projections) | Mapped |
| F-10 | Missing recursive CTE lineage | WP-1 (Database Integrity) | Mapped |

## 2. Revised Work Package Design
**WP-1: Database Integrity & Lineage (Persistence Core)**
* **Scope**: Write explicit `alembic` DDL for all aggregates. Implement `psycopg2` bindings for all Repositories. Explicitly write recursive CTE queries for `fetch_lineage()` over chronological DAGs. Establish Outbox tables.
* **Dependencies**: None.
* **Acceptance Criteria**: `UNIQUE(subject_urn, previous_urn)` database constraints verified. `fetch_lineage()` successfully traverses N=10 chains recursively.

**WP-2: Performance Engine Completion (Regime Ingestion)**
* **Scope**: Expand `PerformanceEvaluation` aggregate to ingest and persist `RegimeDistribution` fractional structs.
* **Dependencies**: WP-1.
* **Acceptance Criteria**: `ForecastError` integrates macro constraints seamlessly.

**WP-3: Attribution Math Completion (Causal Decomposition)**
* **Scope**: Replace hardcoded `{"thesis": 0.5, "luck": 0.5}` floats with actual regression math fetching `Decision Journal` intent, `Decision` slippage, and `FactorModelVersion`.
* **Dependencies**: WP-1, WP-2.
* **Acceptance Criteria**: Differentiates Case A (Thesis failure) from Case B (Execution failure) dynamically.

**WP-4: End-to-End Workflow Edges (Integration)**
* **Scope**: Formally bind the missing structural edges. Specifically bind `Decision Journal -> Decision` by emitting `DecisionIntentReady` to the Execution module, and establish the `Execution -> Outcome` ingestion hook.
* **Dependencies**: WP-1.
* **Acceptance Criteria**: Workflow natively traverses Journal intent cleanly into Execution.

**WP-5: CQRS & Self-Learning Projections**
* **Scope**: Build async `ProjectionWorker` listeners. Persist `ResearchFeedbackCandidateCreated` and `CapabilityFeedbackCandidateCreated` into queryable `research_feedbacks` read-models.
* **Dependencies**: WP-1, WP-3.
* **Acceptance Criteria**: Self-Learning candidates are queryable via REST/RPC models instead of being ephemeral events.

**WP-6: Behavioral Integration Testing**
* **Scope**: Create end-to-end integration tests chaining the engines without stubs.
* **Dependencies**: WP-1 through WP-5.
* **Acceptance Criteria**: Real Postgres OCC constraint violations proven in test suites.

## 3. Workflow Completeness Matrix
| Edge | Current State | Required Remediation | Owning WP |
|------|---------------|----------------------|-----------|
| Research → Thesis | Assumed | N/A (Upstream) | N/A |
| Thesis → Journal | Implemented | None | N/A |
| Journal → Decision | Missing | Create CQRS integration binding Intent to Execution engine. | WP-4 |
| Decision → Execution | Implemented | None | N/A |
| Execution → Outcome | Missing | Bind settlement hooks to Outcome ingestion. | WP-4 |
| Outcome → Performance | Broken | Inject `RegimeDistribution` logic. | WP-2 |
| Performance → Attribution | Broken | Inject dynamic causal algorithms. | WP-3 |
| Attribution → Governance | Stubbed | Replace `pass` projections with actual handlers. | WP-5 |

## 4. Self-Learning Completion Plan
**Path to Usability**:
1. `DecomposeAttributionService` emits `ResearchFeedbackCandidateCreated`.
2. Outbox relay transfers event to RabbitMQ/Kafka.
3. `ResearchFeedbackProjectionWorker` (WP-5) consumes event.
4. Worker transforms payload into `ResearchFeedbackReadModel`.
5. Worker physically inserts row into Postgres `research_feedbacks_projection` table.
6. Downstream LLM pipelines query `fetch_feedback_by_capability()` via `psycopg2` to natively re-train.

## 5. RegimeDistribution Completion Plan
* **Storage Model**: JSONB or Decimal Vector mapping `[Bull, Bear, Sideways]` allocations natively on the `performance_evaluations` table.
* **Persistence Model**: Appended immutably alongside the `ForecastError` inside the CQRS service.
* **Projection Model**: Summarized chronologically per-worker via `PerformanceProjectionWorker`.
* **Replayability Model**: Bound eternally to the URN; fetching a 10-year-old evaluation natively reloads the precise macro distributions present during calculation.

## 6. Decision Journal Integration Plan
**Journal → Decision**: 
When `AppendDecisionJournalService` completes, it publishes `DecisionJournalAppended`. A new integration handler `InitiateDecisionExecutionService` (WP-4) intercepts this event and builds the upstream `Decision` context for the Execution Engine, definitively blocking "Execution without Intent" scenarios.

## 7. Replayability Completion Matrix
* **Hashes**: Covered via recursive CTE SQL queries validating sequential SHA256 matches (WP-1).
* **Lineage**: Covered via `UNIQUE` OCC constraints checking DAG parents (WP-1).
* **Factor Versions**: Covered via foreign-key storage within `AttributionDecomposition` (WP-3).
* **Governance History**: Covered via strict Ledger schema bounds (WP-1).
* **Feedback History**: Covered via read-model persistence tracking exact thesis failures (WP-5).

## 8. Remediation Closure Criteria
1. `alembic` migrations contain actual `CREATE TABLE` and `UNIQUE` constraint DDL.
2. `repositories.py` contains valid `psycopg2` SQL strings for inserts and recursive CTE lineages.
3. `workers.py` contains actual async handlers committing into read-models.
4. All WPs successfully implemented and verified against PostgreSQL integration containers.

## 9. Final Verdict
**READY_FOR_REMEDIATION_IMPLEMENTATION**
