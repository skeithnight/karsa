# ADR-054: Ex-Ante Risk Modeling, Persistence, and Stress-Testing Strategy

## Status
Approved

## Date
2026-06-14

## Context
Designing the analytical plane of the Risk Engine requires defining:
1. **Mathematical Scope**: Incorporating Value at Risk (VaR), Expected Shortfall (CVaR), volatility/correlation forecasting, concentration (HHI/Gini), liquidity risk (ADV/DTL), and stress testing.
2. **Persistence Strategy**: Covariance matrices and stress evaluations can grow large and change frequently. We must decide if they are modeled as append-only ledger entries or versioned projections, and how to store large matrix tables.
3. **Replayability and Auditing**: Compliance requirements demand that we can reconstruct any ex-ante risk estimate calculated years ago to verify that historical trade decisions complied with active limit parameters.
4. **Regime and Macro Integration**: Estimating ex-ante volatility depends heavily on macro regimes (high vs. low vol markets), but the Regime Engine is scheduled for a future sprint.

## Decision
We enforce the following modeling and persistence rules for the Risk Engine:

1. **Ex-Ante Invariant - Append-Only Write-Once Ledger Records**:
   - Risk evaluations are modeled as immutable write-once ledger entries (`RiskEvaluationRecord` aggregate root). 
   - Once calculated, a record is committed to PostgreSQL and never updated or deleted. This guarantees audit durability and hindsight prevention.
   - Version-based modifications (OCC) are entirely bypassed since rows are append-only.

2. **Covariance Matrix Persistence**:
   - Large covariance matrices are stored as immutable JSON/binary payloads in object storage (MinIO/S3), keyed by URN (`urn:karsa:risk:covariance:<uuid>`).
   - PostgreSQL holds metadata entries (`covariance_forecasts` table) linking to the URN, which minimizes database storage bloat and maintains B-tree lookup efficiency.

3. **Deterministic Replayability**:
   - Risk evaluations link URNs representing:
     ```
     RiskEvaluationRecord
       -> PortfolioSnapshot URN (holdings)
       -> MarketAssumptions URN (prices, historical returns)
       -> RegimeState URN (macro scale factor)
       -> RiskEngine Version (semantic code tag)
     ```
   - Standardizing input parameters via URN-referenced immutable inputs ensures that executing the same engine version against the same inputs 5 years later produces identical risk forecasts.

4. **Concentration and Liquidity Modeling**:
   - **Concentration**: Modeled at asset, sector, and strategy levels using the Herfindahl-Hirschman Index (HHI) and Gini coefficient computed dynamically from the portfolio snapshot.
   - **Liquidity**: Modeled by mapping holding sizes against Average Daily Volume (ADV) to produce a Days-to-Liquidate (DTL) exposure metric under baseline and stress assumptions.

5. **Stress Testing**:
   - Stress testing definitions (e.g. macro shock parameters) are managed as static configuration assets in a registry.
   - Stress test evaluations are generated on-demand against target portfolio snapshots and stored as immutable `StressEvaluationRecord` ledger rows.

6. **Regime Decoupling Fallback**:
   - Until the Regime Engine is implemented, the Risk Engine utilizes a constant baseline regime multiplier ($1.0$) stored in configuration. This decouples Sprint-40 execution from downstream sprints.

## Consequences
- **Perfect Audit Trail**: Ex-ante estimates are historically preserved, enabling clear validation against subsequent ex-post realized drawdowns.
- **Optimized Storage Profile**: Avoids slow and bloated database table updates for multi-asset covariance matrices.
- **Scale-Ready Analytics**: Decoupled macro regimes and on-demand stress testing support future expansion without database modifications.
