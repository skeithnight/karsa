# Investment Mandate

**Document Type:** Static Context (Layer 1)
**Purpose:** Injected into every agent prompt as immutable fund rules
**Owner:** CIO
**Last Updated:** 2026-06-21

---

## Fund Definition

| Parameter | Value |
|---|---|
| Fund Name | KARSA Growth Fund |
| Base Currency | IDR (Indonesian Rupiah) |
| Benchmark | IHSG (Indonesia Composite Index) |
| Fund Size | IDR 10B (example) |
| Investment Horizon | 1-5 years (medium term) |
| Leverage | Not allowed |

---

## Investment Universe

### Allowed

- IDX-listed equities only
- Market cap > IDR 5T
- Minimum daily trading volume: IDR 1B
- Must be in IHSG constituent or MSCI Indonesia Index

### Excluded

- Penny stocks (price < IDR 100)
- Stocks with trading halts in last 6 months
- Companies with audit qualifications
- Companies under BPK investigation

---

## Sector Limits

| Sector | Maximum Allocation | Current Target |
|---|---|---|
| Finance (Banking + Insurance) | 30% | 25% |
| Energy (Oil, Gas, Coal, Mining) | 20% | 15% |
| Consumer (FMCG, Retail, F&B) | 25% | 20% |
| Technology | 15% | 12% |
| Infrastructure | 15% | 10% |
| Other | 15% | 18% |

---

## Concentration Rules

| Rule | Limit |
|---|---|
| Single stock maximum | 3% of portfolio |
| Top 5 holdings | 60% of portfolio |
| Top 10 holdings | 80% of portfolio |
| Sector maximum | Per table above |
| Cash minimum | 2% of portfolio |

---

## Rebalance Triggers

- Quarterly scheduled rebalance
- Any single position exceeds 30% above target weight
- Sector allocation breaches limit
- MSCI reclassification event
- Dividend ex-date (for dividend reinvestment)

---

## Conglomerate Exposure

IDX has significant conglomerate cross-holdings. Track total exposure:

| Group | Key Tickers | Max Group Exposure |
|---|---|---|
| Djarum/BCA | BBCA, BGTN | 15% |
| Astra | ASII, AUTO, SMSM | 12% |
| Sinar Mas | BMRI, SMGR, Djarum | 10% |
| Salim | ICBP, INDF | 8% |
| Lippo | LPKR, LPPF | 5% |
| Prajogo | MEDC, MBSS | 8% |
| Bakrie | BKSL, BIPI, ANTM | 5% |

---

## Dividend Policy

- Dividend reinvestment: Yes (compounding)
- Track ex-dates for 58-stock universe
- Minimum yield threshold for dividend strategy: 3%
- Tax: 10% withholding for holdings > 1 year

---

## MSCI Considerations

- Monitor free-float requirements (minimum 15%)
- Track MSCI quarterly rebalancing schedule
- Flag stocks at risk of downgrade (free-float < 18%)
- Foreign ownership limits affect MSCI weight

---

## Decision Framework Summary

```
Entry Criteria:
  - Dividend yield + growth rate + valuation vs historical range
  - At least 2/4 analyst agents agree positively
  - Risk officer approves position size

Exit Criteria:
  - Dividend cut announced
  - MSCI downgrade
  - Rupiah weakness > 2% weekly
  - Technical support break (stop-loss)
  - Position exceeds holding period limit

Position Sizing:
  - Kelly criterion on historical volatility
  - Maximum 3% per stock
  - Adjust for correlation with existing holdings
```
