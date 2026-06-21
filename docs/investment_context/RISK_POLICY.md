# Risk Policy

**Document Type:** Static Context (Layer 1)
**Purpose:** Defines risk limits and compliance rules for agent decisions
**Owner:** Risk Officer / CIO
**Last Updated:** 2026-06-21

---

## Portfolio Risk Limits

| Metric | Limit | Measurement |
|---|---|---|
| Annual Volatility | 22% max | 252-day rolling |
| Maximum Drawdown | 15% | Peak-to-trough |
| Beta (vs IHSG) | 0.8 - 1.3 | 60-day rolling |
| Sector Correlation | < 0.7 | Pairwise, same-sector holdings |
| Liquidity | Closeable in < 5 days | Based on average daily volume |
| VaR (95%, 1-day) | 2% of NAV | Historical simulation |

---

## Position Risk Rules

### Entry Rules

| Rule | Threshold |
|---|---|
| Minimum conviction score | 6/10 (from analyst consensus) |
| Minimum margin of safety | 10% below intrinsic value |
| Maximum entry price deviation | 5% from 52-week average |
| Required approvals | Risk Officer + Portfolio Manager |

### Exit Rules

| Trigger | Action |
|---|---|
| Stop-loss hit | Auto-sell at market |
| Target price reached | Review for partial/full exit |
| Dividend cut | Exit within 5 trading days |
| MSCI downgrade | Exit within 10 trading days |
| Rupiah crash (>5% weekly) | Reduce all positions by 20% |
| Mandate breach | Immediate corrective action |

### Position Sizing

```
Kelly Criterion Formula:
  f* = (bp - q) / b

Where:
  b = odds (target price / entry price - 1)
  p = probability of hitting target (from conviction score)
  q = 1 - p

Adjusted:
  f_adj = f* * 0.5  (half-Kelly for safety)
  f_final = min(f_adj, 3%)  (cap at single-stock limit)
```

---

## Sector Risk Monitoring

### Daily Checks

- [ ] No sector exceeds limit
- [ ] Top 5 concentration within 60%
- [ ] All positions above minimum liquidity threshold
- [ ] Portfolio beta within 0.8-1.3
- [ ] No single-day loss > 2% of NAV

### Weekly Checks

- [ ] Correlation matrix updated
- [ ] Drawdown within 15% limit
- [ ] Rupiah exposure assessed
- [ ] Conglomerate cross-exposure reviewed
- [ ] MSCI float risk reviewed

---

## Escalation Matrix

| Severity | Trigger | Action | Timeline |
|---|---|---|---|
| GREEN | All metrics within limits | Continue monitoring | Daily |
| AMBER | Metric within 10% of limit | Alert CIO, increase monitoring | Same day |
| RED | Metric breaches limit | Halt new positions, corrective action | Immediate |
| CRITICAL | Multiple breaches or drawdown > 10% | Emergency committee review | Within 1 hour |

---

## Mandate Compliance Checklist

Every investment decision must pass:

- [ ] Stock in allowed universe (IDX, market cap > IDR 5T)
- [ ] Sector allocation within limit after trade
- [ ] Single stock position ≤ 3%
- [ ] Top 5 concentration ≤ 60%
- [ ] Conglomerate group exposure within limit
- [ ] Liquidity: position closeable in < 5 days
- [ ] No active trading halt
- [ ] No audit qualification
- [ ] Minimum conviction score met (6/10)

---

## Risk Officer Veto Criteria

The Risk Officer MUST veto if:

1. Any mandate compliance check fails
2. Position would breach sector limit
3. Portfolio beta would exceed 1.3
4. Liquidity insufficient for position size
5. Conglomerate exposure would exceed limit
6. Conviction score below minimum threshold

The Risk Officer MAY veto if:

1. Macro environment unfavorable
2. Correlation with existing holdings too high
3. Unusual volume or price action detected
4. News flow suggests elevated near-term risk
