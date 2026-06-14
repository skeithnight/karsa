# ADR-053: Risk Engine Bounded Context Boundaries and Ownership

## Status
Approved

## Date
2026-06-14

## Context
As Karsa scales towards a Virtual Investment Firm (VIF), we require a dedicated, isolated subsystem to manage ex-ante risk analytics (Value at Risk, stress testing, exposure, concentration, and liquidity risk). 

Risk analysis must be decoupled from transactional execution, portfolio accounting, realized performance calculation, and limit enforcement. To achieve high operational robustness and architectural decoupling, we must establish strict boundaries around what the Risk Engine owns and does not own, and audit its dependency paths.

## Decision
We enforce the following bounded context boundaries and ownership rules for the Risk Engine:

1. **Analytical Ex-Ante Focus**:
   - The **Risk Engine Bounded Context** is the sole writer and authoritative owner of ex-ante risk models, forecasts, stress evaluations, and parameter covariance matrices.
   - It is strictly prohibited from owning, writing to, or managing:
     - Realized performance ( Sharpe, Sortino, realized drawdowns - owned by **Performance Engine**).
     - Causal realized factors (owned by **Attribution Engine**).
     - Active portfolio holdings, NAV, or cash transactions (owned by **Portfolio Engine**).
     - Limits, policies, and active compliance enforcement (owned by **Governance Engine**).
     - Budget updates or allocation weights optimization (owned by **Capital Allocation Engine**).

2. **Decoupled Read-Only Ingestion Paths**:
   - **Portfolio Engine Ingestion**: Risk consumes portfolio snapshots to compute concentration, exposures, and VaR. Risk is a read-only consumer and cannot mutate holdings.
   - **Performance Engine Ingestion**: Risk reads historical realized returns to update covariance matrices and estimate asset-level volatility parameters.
   - **Regime Engine Ingestion**: Risk reads macro classification states to scale asset-level volatility forecasts.
   - **Decision Journal & CIO Ingestion**: Risk reads target risk budgets and pre-outcome expectations for ex-ante validation check comparisons.

3. **Downstream Consumption Paths**:
   - Risk publishes `RiskEvaluationCreatedEvent` and `CovarianceForecastUpdatedEvent` containing ex-ante risk estimates.
   - **Governance** consumes VaR to check ex-ante limits. Governance cannot modify Risk parameters or database entries.
   - **Capital Allocation** consumes covariance forecasts to optimize target asset weights.

4. **Prohibited Dependencies**:
   - **Post-Mortem Engine**: Post-Mortem can only read historical Risk records during failure analysis; it cannot write to Risk databases.
   - **Direct database updates**: External contexts are prohibited from directly editing database tables managed by the Risk Engine.

## Consequences
- **Decoupled Risk Analysis**: Limit checks and asset weighting do not introduce mutative dependencies into the core analytical loop.
- **Zero Realized Infiltration**: Ex-ante estimates remain statistically isolated from historical evaluation, avoiding hindsight pollution.
- **High Schema Isolation**: The risk database holds only risk snapshots and forecasts, keeping query profiles highly efficient.
