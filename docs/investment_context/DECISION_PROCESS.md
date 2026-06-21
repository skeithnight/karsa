# Decision Process

**Document Type:** Static Context (Layer 1)
**Purpose:** Defines the investment decision workflow from analysis to execution
**Owner:** Portfolio Manager / CIO
**Last Updated:** 2026-06-21

---

## Workflow Overview

```
TRIGGER: User query or scheduled daily review
    │
    ▼
PHASE 1: Parallel Analysis (2-3 min)
    │
    ▼
PHASE 2: Researcher Debate (1-2 min)
    │
    ▼
PHASE 3: Portfolio Manager Synthesis (2 min)
    │
    ▼
PHASE 4: Risk Officer Veto (30 sec)
    │
    ▼
PHASE 5: Committee Chair Review (1 min)
    │
    ▼
PHASE 6: Execution (if approved)
    │
    ▼
PHASE 7: Monitoring (daily)
```

---

## Phase 1: Parallel Analysis

Four analyst agents run simultaneously on the target ticker.

### Fundamental Analyst

**Input:** Ticker symbol
**Tools:** YFinance (financials), IDX company reports
**Output:**
- P/E ratio vs 5-year average
- Dividend yield
- ROE vs WACC
- Free cash flow yield
- Revenue/EPS growth rate
- Intrinsic value estimate
- Margin of safety percentage

**Confidence:** 8/10 (historical data reliable)

### Technical Analyst

**Input:** Ticker symbol, OHLCV data
**Tools:** YFinance (OHLCV), technical indicators
**Output:**
- RSI (30-70 scale)
- MACD trend direction
- Bollinger Band position
- Support/resistance levels
- Trend strength (ADX)
- Entry/exit price levels
- Holding period estimate

**Confidence:** 6/10 (IDX more volatile than developed markets)

### Sentiment Analyst

**Input:** Ticker symbol
**Tools:** Web search (news), StockTwits, Reddit
**Output:**
- News sentiment score (-100 to +100)
- Retail vs institutional tone
- Recent catalysts (mergers, guidance, regulatory)
- Short-term momentum (1-4 week)
- Long-term thesis strength

**Confidence:** 5/10 (Indonesian sentiment data sparse)

### Market Context Agent

**Input:** Portfolio state
**Tools:** Macro feeds (rates, FX, commodities)
**Output:**
- Macro regime (risk-on / risk-off)
- Rupiah vs USD trend
- BIS rate curve shape
- Sector rotation signals
- Commodity price impact on IDX sectors

**Confidence:** 7/10 (macro data publicly available)

---

## Phase 2: Researcher Debate

Two researcher agents debate using Phase 1 outputs.

### Bull Researcher

**Input:** All 4 analyst outputs
**Task:** Build case FOR investment
**Output:**
- Bull memo (500 words max)
- Key catalysts
- Upside scenario with price target
- Conviction level (STRONG if 3/4 analysts agree)

### Bear Researcher

**Input:** All 4 analyst outputs
**Task:** Build case AGAINST investment
**Output:**
- Bear memo (500 words max)
- Key risks and headwinds
- Downside scenario with price target
- Missing catalysts
- What could go wrong

### Debate Rounds

- Round 1: Each presents case
- Round 2 (optional): Each responds to other's points
- Final: Synthesis of both perspectives

---

## Phase 3: Portfolio Manager Synthesis

**Input:** Bull memo, Bear memo, current portfolio state
**Task:** Make final decision

### Decision Matrix

| Bull Conviction | Bear Conviction | Decision |
|---|---|---|
| STRONG | Weak | BUY (Strong) |
| STRONG | Medium | BUY (Medium) |
| Medium | Weak | BUY (Medium) |
| Medium | Medium | HOLD or PASS |
| Weak | Strong | SELL or PASS |
| Weak | Medium | PASS |
| Any | STRONG | SELL (if held) or PASS |

### Output: Investment Memo

```
TICKER: [symbol]
DECISION: [BUY/HOLD/SELL/PASS]
CONVICTION: [STRONG/MEDIUM/WEAK]
ENTRY PRICE: [range]
EXIT TARGET: [price]
STOP LOSS: [price]
POSITION SIZE: [% of portfolio]
THESIS: [3-4 sentences]
KEY METRICS: {pe, dividend_yield, roe, fcf_yield}
RISKS: [list]
NEXT REVIEW: [date]
```

---

## Phase 4: Risk Officer Veto

**Input:** Investment memo + mandate rules
**Task:** Verify compliance

### Checklist

- [ ] Position size ≤ 3%
- [ ] Sector within limit
- [ ] Top 5 concentration ≤ 60%
- [ ] Liquidity sufficient
- [ ] Beta within range
- [ ] Conglomerate exposure OK
- [ ] Conviction ≥ 6/10

### Decisions

- **APPROVED:** All checks pass
- **REVISION NEEDED:** Minor violation, PM adjusts
- **REJECTED:** Major violation, filed for review

---

## Phase 5: Committee Chair Review

**Input:** Full memo chain (analyst outputs + debate + PM decision + risk check)
**Task:** Final sign-off

### Review Criteria

- Logic consistency across all stages
- No hallucinated data or metrics
- Mandate compliance verified
- Risk assessment reasonable
- Thesis supported by evidence

### Decisions

- **APPROVED:** Ready for execution
- **HOLD:** Re-analysis next week
- **REVISE:** Back to PM
- **REJECTED:** Filed with reason

---

## Phase 6: Execution

**Input:** Approved memo
**Task:** Place order (when live) or log decision

### Steps

1. Construct order (ticker, quantity, price, type)
2. Final risk check (margin, liquidity)
3. Log to audit trail
4. Execute via broker API (when production)
5. Record fill details
6. Update memo with execution data

---

## Phase 7: Monitoring

**Frequency:** Daily for all active positions

### Daily Checks

- Current price vs entry/target/stop-loss
- Fundamental trigger events (dividend, guidance, regulatory)
- Technical breaks (support/resistance)
- Macro changes (rupiah, rates, sector rotation)

### Trigger Actions

If any trigger hit:
1. Generate re-analysis
2. Update conviction and price target
3. Execute exit if risk limit breached
4. Close memo and record realized return

---

## Conviction Scoring

| Level | Criteria | Win Rate Target |
|---|---|---|
| STRONG | 3-4 analysts agree positively | > 65% |
| MEDIUM | 2 analysts agree positively | > 55% |
| WEAK | 1 analyst agrees, contrarian call | > 45% |

Conviction is calibrated against realized returns:
- If STRONG decisions win < 60%, recalibrate
- If WEAK decisions win > 50%, recalibrate
