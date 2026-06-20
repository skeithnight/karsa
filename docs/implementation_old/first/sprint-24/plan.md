# Sprint-24 Performance Engine Foundation Plan

## 1. Context & Scope
This sprint is designated as **DESIGN ONLY**.
In accordance with the repository constraints:
- No production code, database migrations, or test code will be generated or executed.
- The sole objective is to design the architectural foundations for the **Performance Engine Foundation**.
- The architecture package will stop at the `ARCHITECTURE_FREEZE` transition.

The Performance Engine is the authoritative context responsible for evaluating the quality of decisions, theses, workers, providers, strategies, portfolios, and future agents. It consumes outcomes and outputs evaluations without executing trades or managing capital.

## 2. Objectives
- Define context ownership boundaries between Performance, Attribution, Thesis, Governance, and Review contexts.
- Establish the domain model for Performance management, establishing `DecisionEvaluation` and `EvaluationSnapshot` as aggregate roots.
- Design metrics schemas separating Thesis Quality, Execution Quality, and Allocation Quality.
- Formulate the Confidence Calibration model, mapping historical predictions and outcomes to calibrated ratings partitioned by regime and version.
- Design benchmark comparison abstractions (SPY, QQQ, custom indices).
- Outline the read-side projections for worker, thesis, and strategy rankings.
- Establish persistence schemas, events, sequence diagrams, and concurrency controls.
- Author Architectural Decision Records (ADRs) to lock the design.

## 3. Architecture Alignment
The Performance Engine consumes execution telemetry and outcomes from other platform contexts to execute calibration and accuracy scoring.

Canonical architectural documentation will be stored in:
- [14-performance-engine.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/14-performance-engine.md)

Related ADRs:
- [ADR-031: Performance Engine Context Ownership and Boundaries](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-031-performance-engine-ownership.md)
- [ADR-032: Performance Evaluation and Confidence Calibration Model](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-032-performance-evaluation-model.md)

## 4. Bounded Context Deliverables
- **Evaluation & Measurement Context**: Computes and stores accuracy scores, hit rates, drawdowns, and calibration stats.
- **Benchmark Registry Context**: Manages index price series and evaluates excess returns.
- **Rankings & Projections Context**: Computes read-side dashboards for thesis, worker, and strategy leaderboard queries.

## 5. Work Packages (Design-Only)
- **WP-24.1**: Domain modeling of `DecisionEvaluation` aggregates, `EvaluationSnapshot`, and dimension tags.
- **WP-24.2**: Metrics definitions and schema layout (Thesis, Execution, and Allocation Quality separation).
- **WP-24.3**: Confidence calibration algorithms, prediction-to-outcome mapping, and market regime conditioning.
- **WP-24.4**: Benchmark comparisons framework and index parsing boundaries.
- **WP-24.5**: Challenge matrix review and ADR drafting.
