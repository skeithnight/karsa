# Sprint-40 Risk Engine Foundation Implementation Report

This document reports on the implementation of the **Risk Engine Foundation** bounded context in Sprint-40.

---

## 1. Executive Summary
The Risk Engine bounded context acts as the ex-ante analytical plane of the Virtual Investment Firm (VIF), modeling forward-looking risk estimates. It remains decoupled from external execution or downstream contexts (such as Portfolio, CIO, Decision Journal, Attribution, and Post-Mortem).

The implementation satisfies all architectural constraints, featuring strictly append-only/immutable aggregates, covariance estimation, stress scenario evaluations, concentration indices, and liquidity risk.

---

## 2. Codebase Organization
The package is located at `src/karsa/risk/` and contains the following modules:

* [__init__.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/risk/__init__.py): Package entry point configuring router imports and dependencies.
* [exceptions.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/risk/exceptions.py): Domain-specific exceptions (`ImmutabilityViolationException`, `NegativeEigenvalueException`, `InvalidSnapshotURNException`, `InvalidValueException`).
* [value_objects.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/risk/value_objects.py): Immutable value objects representing risk statistics, including:
  - `ValueAtRisk`
  - `ExpectedShortfall`
  - `VolatilityForecast`
  - `CorrelationForecast`
  - `ConcentrationRisk`
  - `LiquidityRisk`
  - `StressScenarioResult`
  - `RegimeReference`
  - `AssetExposure`
* [models.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/risk/models.py): Domain aggregates extending `ImmutableAggregate` to enforce runtime read-only protection:
  - `RiskEvaluationRecord` (contains required metadata URNs)
  - `CovarianceForecast`
  - `StressEvaluationRecord`
* [events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/risk/events.py): Core event contracts (`RiskEvaluationCreatedEvent`, `StressEvaluationCreatedEvent`, `CovarianceForecastUpdatedEvent`).
* [ports.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/risk/ports.py): Inbound and outbound abstract boundary ports (`EventPublisherPort`, `ReturnsDataPort`, `RegimeStatePort`, `ObjectStorePort`).
* [repositories.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/risk/repositories.py): Persistence repositories with dual `InMemory` and PostgreSQL implementations.
* [services.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/risk/services.py): Core analytics services:
  - `ConcentrationRiskService`: Evaluates HHI, Gini coefficients, and Top-5 weighting.
  - `LiquidityRiskService`: Projects Days-to-Liquidate under standard and stressed scenarios.
  - `StressTestingService`: Evaluates shocks across portfolio exposures.
  - `RiskEvaluationService`: Orchestrates parametric portfolio risk (VaR, CVaR).
  - `CovarianceForecastService`: Builds EWMA covariance matrix arrays.
* [projections.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/risk/projections.py): Read-only summary projections (`RiskSummaryProjection`).
* [api.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/risk/api.py): FastAPI Presentation API exposure.

---

## 3. Core Calculations & Domain Logic

### Parametric Value at Risk (VaR) & Expected Shortfall (ES)
Risk calculations scale using active macro regime multipliers fetched via the `RegimeStatePort`.
* **Variance Calculation**:
  $$\sigma_p^2 = \sum_i \sum_j w_i w_j \sigma_{ij}$$
* **Vol Adjustments**:
  $$\sigma_{\text{adjusted}} = \sigma_p \times \text{Regime Volatility Multiplier}$$
* **VaR Formula**:
  $$\text{VaR}_{\alpha} = z_{\alpha} \times \sigma_{\text{adjusted}}$$
  where $z_{0.95} = 1.645$, $z_{0.99} = 2.326$.
* **Expected Shortfall (ES) Formula**:
  $$\text{ES}_{\alpha} = \sigma_{\text{adjusted}} \times \left( \frac{\phi(z_{\alpha})}{1 - \alpha} \right)$$
  where $\phi(x) = \frac{1}{\sqrt{2\pi}} e^{-x^2 / 2}$ is the standard normal PDF.

### Concentration Analytics
Calculates concentration parameters dynamically:
* **HHI**:
  $$\text{HHI} = \sum_i w_i^2$$
* **Gini Coefficient**:
  $$\text{Gini} = \frac{\sum_i (2i - n - 1) x_i}{n \sum_i x_i}$$
  for sorted normalized weights $x_1 \le x_2 \le \dots \le x_n$.
* **Top 5 Weight**: Cumulative weight of the top 5 largest holdings.

### Liquidity Risk Analytics
Calculates Days-to-Liquidate (DTL) using Average Daily Volume (ADV):
$$\text{DTL} = \frac{\text{Exposure Nominal Value} \times \text{Liquidation Percent}}{\text{ADV}}$$
If ADV is zero or missing, it falls back to a predefined constant days value (e.g., 99.0).

---

## 4. Database Schema and Immutability
No runtime migrations or schema generation occur at start up. Database updates are strictly migration-based:
* **RiskEvaluationRecord**: Partitioned table by `created_at` (range partition).
* **Immutability Enforcement**: The schema enforces that records in tables `risk_evaluation_records`, `covariance_forecasts`, and `stress_evaluation_records` are strictly read-only. Database trigger `block_risk_record_mutation()` raises exceptions on any `UPDATE` or `DELETE` attempt.
* **1:1 Cardinality**: Uniqueness trigger `enforce_unique_portfolio_snapshot_id` prevents duplicate risk calculations on the same portfolio snapshot URN.

---

## 5. Event and Replay Contracts
Events implement base tracking variables (`event_id`, `correlation_id`, `causation_id`, `event_version`). Replaying evaluations recovers identical calculations using persistent URN tags linked inside the evaluation metadata.
