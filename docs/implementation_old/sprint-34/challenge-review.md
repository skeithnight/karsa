# Sprint-34 Portfolio Engine Challenge Review

This document reviews the core architectural challenges and aggregate boundary decisions for the **Portfolio Engine** to ensure alignment with VIF standards.

---

## 1. Resolution of Mandatory Architecture Challenges

### Challenge #1: Can NAV ownership belong somewhere else?
* **Evaluation**: Net Asset Value (NAV) is calculated as:
  $$\text{NAV} = \text{Total Assets} - \text{Total Liabilities}$$
  This is a direct mathematical derivation of current asset holdings, current valuations, and cash balances.
* **Proof**: The Portfolio Engine is the sole Bounded Context that owns positions and cash balances. Reassigning NAV ownership to another context (such as Performance) would require that context to query Portfolio for holdings or duplicate the transaction ledger. This would violate Bounded Context boundaries and create high-latency API dependencies. Thus, Portfolio is the only logical and correct owner of NAV.

### Challenge #2: Can Performance reconstruct NAV itself?
* **Evaluation**: Performance could theoretically reconstruct NAV by subscribing to `OrderFilledEvents` and cash transactions, maintaining its own shadow transaction ledger.
* **Decision**: **REJECTED**. Maintaining shadow ledger states in the Performance context leads to double-bookkeeping, data inconsistency risks (e.g., pricing timing differences, currency conversions, and rounding issues), and redundant computational overhead. The Performance Engine must remain an analytical context that consumes pre-calculated, authoritative NAV snapshot values.

### Challenge #3: Can Execution own active positions?
* **Evaluation**: Execution could track fills and keep a running total of active positions.
* **Decision**: **REJECTED**. The Execution Engine is a stateless router and Policy Enforcement Point (PEP) for transaction events. Forcing Execution to track active positions would require it to handle cash balances, settlements, corporate actions, and dividend distributions, violating the Single Responsibility Principle. Keeping Execution focused purely on transaction requests and fills is crucial for low-latency pre-trade check scalability.

### Challenge #4: Should exposure calculations belong to Portfolio or Future Risk Engine?
* **Ownership Analysis**:
  * **Linear, Deterministic Exposures**: Simple, historical exposures based on asset weightings or sector breakdowns (e.g., "Tech sector weight = 15%") are calculated deterministically from current positions and asset values. These belong to the **Portfolio Engine** as part of its RTBOR duties.
  * **Non-linear, Predictive Exposures**: Ex-ante factor exposures, beta sensitivities, scenario analysis, and statistical risk measures (VaR) belong to the **Risk Engine** as defined in [ADR-049](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-049-risk-ownership.md).

### Challenge #5: Can Portfolio exist without Benchmark Registry?
* **Evaluation**: The Portfolio Engine can manage cash and position units without a benchmark registry. However, to evaluate relative exposures, benchmark comparison snapshots, and tracking error in real-time, the platform requires a reference index level.
* **Decision**: The Portfolio Engine will include a lightweight **Benchmark Registry**. This registry stores benchmark mappings (e.g., SPY, QQQ) and their levels at valuation time, ensuring that valuation snapshots capture index levels at the exact moment of calculation, guaranteeing auditability.

### Challenge #6: Can Portfolio replay historical states deterministically?
* **Replayability Model Proof**:
  * Let the state of the portfolio at time $T$ be represented as:
    $$S_T = f(S_0, E_1, E_2, \dots, E_n)$$
    where $S_0$ is the initial cash deposit state and $E_i$ are discrete transaction events (fills, cash debits/credits) up to time $T$.
  * By writing all transactions to append-only ledgers and verifying the `aggregate_version` with Optimistic Concurrency Control (OCC), we guarantee that the transaction log is an immutable and ordered history of state changes. Replaying this log from $T_0$ to $T_1$ will always reconstruct the exact positions, cash balances, and NAV at $T_1$.

---

## 2. Challenge of Aggregate Boundaries

### Decoupled Positions Aggregate
* **Design Decision**: Model [PositionAggregate](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/domain/model/position.py) as a standalone aggregate root separate from [PortfolioAggregate](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/domain/model/portfolio.py).
* **Rationale**: If positions were nested child entities of the Portfolio aggregate root, any trade fill would require locking the entire portfolio, causing write bottlenecks and high rate OCC conflicts. Restricting the boundary of `PositionAggregate` to a single asset (e.g. AAPL) isolates lock contention to updates for that specific asset.

### Write-Once Valuation Aggregate
* **Design Decision**: Model [ValuationAggregate](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/domain/model/valuation.py) as an immutable, write-once snapshot record.
* **Rationale**: Valuations must represent a frozen state of the portfolio at a point in time. Prohibiting updates to historical valuation records protects ledger history from alterations, ensuring auditability.

---

## 3. Dependency Proof: Why Portfolio Foundation Precedes Performance Evolution

The VIF architecture requires the Portfolio Engine to be implemented before the Performance Engine is evolved:

```
+------------------+     +-----------------------+     +--------------------+
| Execution Engine | --> | Portfolio Engine (RTB) | --> | Performance Engine |
| (Fills Logged)   |     | (NAV Calculated)      |     | (Returns Computed) |
+------------------+     +-----------------------+     +--------------------+
```

1. The Performance Engine calculates ex-post metrics (returns, Sharpe, Sortino, drawdowns) using the change in portfolio Net Asset Value (NAV).
2. The returns calculation formula requires NAV as the input:
   $$R_t = \frac{\text{NAV}_t - \text{NAV}_{t-1} + C_t}{\text{NAV}_{t-1}}$$
   where $C_t$ represents net cash flows.
3. If the Portfolio Engine is not implemented, the Performance Engine has no source for the authoritative $\text{NAV}_t$ denominator. 
4. Therefore, the Portfolio Engine RTBOR must be established first to calculate and publish NAV valuations, resolving the dependency chain.

---

## 4. ADR-049 Alignment Validation

This design complies with the rules of [ADR-049](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-049-risk-ownership.md):
* **Computational Decoupling**: Portfolio exposes holdings and simple exposure snapshots. It does not compute ex-ante VaR statistics or run Monte Carlo simulations.
* **Stateless Risk**: The future Risk Engine (Sprint-36) will consume holdings snapshots from Portfolio to calculate statistical risk metrics, keeping the transactional ledger (RTBOR) clean, fast, and lock-free.
