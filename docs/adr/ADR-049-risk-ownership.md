# ADR-049: Risk Bounded Context and Ownership Foundation

## Status
Frozen

## Date
2026-06-14

## Context
Ex-ante risk calculation (Value at Risk (VaR), Expected Shortfall, scenario stress testing, concentration risk, and factor risk models) has ambiguous boundaries across Portfolio, Capital Allocation, and Governance. We must re-evaluate risk ownership from first principles to determine whether it belongs inside an existing context or as a standalone first-class bounded context, and resolve the resulting roadmap sequencing.

## Decision
We select **Option B: Dedicated Risk Engine Bounded Context**. It is a first-class bounded context.

We enforce the following architectural rules:
1. **Risk Engine (Predictive Analytics)**: Owns ex-ante risk models (Monte Carlo VaR, parametric risk, stress testing, scenario simulation, covariance forecasts). It consumes holdings from the Portfolio Engine and publishes calculated risk statistics to the `risk_records` ledger.
2. **Portfolio Engine (RTBOR)**: Owns actual holdings, cash ledgers, and sector/factor exposures. It does **not** run predictive risk models or simulate scenarios.
3. **Governance Engine (Preventive Enforcement)**: Defines policy limits (e.g. max VaR caps) and validates them at the Execution PEP. It consumes risk metrics from the Risk Engine for PDP compliance checks, but does not calculate them.
4. **Capital Allocation Engine (Optimization Solvers)**: Consumes covariance matrices and risk forecasts from the Risk Engine to run portfolio weight optimizations.

### First-Principles Challenge Evaluation
* **Capital Allocation Dependency**: Capital Allocation optimization solvers require risk forecasts and covariance matrices as inputs. Without a dedicated Risk context owning these calculations, Capital Allocation would have to write and run its own predictive risk models, violating the single-responsibility principle.
* **Governance Dependency**: Governance enforces limits but does not calculate exposures. We isolate **Risk Measurement** (Risk Engine) from **Risk Enforcement** (Governance PDP/PEP).
* **Portfolio vs. Risk (CPU & Workload Isolation)**: Ex-ante VaR simulations are computationally expensive. Separating Risk from Portfolio prevents CPU-heavy simulations from blocking high-speed holdings updates in the RTBOR.
* **Performance vs. Risk**: Performance Engine owns ex-post historical outcome analytics (Sharpe, Drawdowns). The Risk Engine owns ex-ante forward-looking predictive analytics (VaR, scenarios). Mixing them violates conceptual separation.
* **Regime vs. Risk**: Regime Engine owns macro classification (e.g. identifying high volatility states), whereas Risk Engine owns portfolio-specific exposure simulations.

## Roadmap sequencing
The introduction of the Risk Engine extends the target roadmap to 40 Sprints, placing **Sprint-36: Risk Engine Foundation** immediately after Sprint-35 Performance Engine, ensuring that position ledgers (Portfolio) and returns series (Performance) exist before portfolio risk simulations are modeled.

## Consequences
- **Decoupled Analytics**: Portfolio ledger writes remain highly scalable and lock-free.
- **Compute Isolation**: Risk Engine can run on compute-optimized nodes without impacting transaction pipelines.
- **Auditable History**: Calculated risk states are written to the append-only `risk_records` ledger, preserving a complete audit trail of portfolio risk profiles.
