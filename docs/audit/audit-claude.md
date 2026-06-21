# KARSA Investment Firm Agent Dashboard - Comprehensive Audit & Enhancement Report

**Generated:** June 2026  
**Repository:** github.com/skeithnight/karsa (master branch)  
**Scope:** Investment Platform Evolution → CIO Dashboard & Agent Intelligence  
**Target:** Enterprise-Grade Investment Firm Operations with Easy Executive Understanding

---

## EXECUTIVE SUMMARY

Karsa is well-architected as an enterprise orchestration framework with strong governance discipline. However, to function as a true **Investment Firm Agent** with a **CIO-friendly dashboard**, the platform requires:

1. **Agent Architecture Expansion** — Specialized investment analyst agents with debate & synthesis patterns
2. **Dashboard Domain Specialization** — IDX/investment-specific metrics, entry/exit signals, conviction scoring
3. **Knowledge & Memory Systems** — RAG-backed research library, persistent decision logs, performance attribution
4. **Decision Pipeline** — Deterministic investment workflows combining agent outputs into actionable theses
5. **Governance Integration** — Investment memos, mandate compliance, audit trails for every recommendation

**Current Risk:** The platform has governance rigor but lacks investment domain logic and CIO-facing metrics. The web console shows agent state but not investment decisions a CIO actually needs (buy/sell price, conviction, risk-adjusted returns).

---

## PART 1: CURRENT STATE ANALYSIS

### 1.1 Strengths

#### Architecture & Governance
- ✅ **Event-sourced design** provides immutable decision audit trail
- ✅ **Strict sprint lifecycle** (DESIGN → AUDIT → IMPLEMENT → VERIFY → CLOSE) enforces quality gates
- ✅ **Bounded contexts** cleanly separate control, execution, and presentation layers
- ✅ **DTO → ViewModel mapping** provides defensive data coalescing against malformed payloads
- ✅ **Static export** Next.js strategy eliminates runtime server dependency

#### Technical Foundation
- ✅ **Python backend** with Redis pub/sub scales agent coordination across workers
- ✅ **PostgreSQL + TimescaleDB** handles time-series market data
- ✅ **Docker multicontainer** orchestration ready for production deployment
- ✅ **Zustand + TanStack Query** provides battle-tested state & server sync
- ✅ **AG Grid integration** ready for large financial datasets

### 1.2 Critical Gaps (Investment Domain)

| Gap | Severity | Impact | Current State |
|-----|----------|--------|----------------|
| **No Specialized Analyst Agents** | CRITICAL | Cannot generate credible buy/sell recommendations | Generic orchestration only |
| **Missing Investment Signals** | CRITICAL | Dashboard shows no entry/exit prices or conviction | Governance metrics only, no trading logic |
| **No RAG Knowledge System** | HIGH | Agents cannot learn from historical memos/research | Stateless agent calls per request |
| **No Performance Attribution** | HIGH | Cannot decompose returns (selection, allocation, beta) | Event sourcing exists but not leveraged for this |
| **Memo → Action Pipeline Missing** | HIGH | Agents write decisions but no structured workflow to convert them to trades | One-way output |
| **No IDX Domain Context** | MEDIUM | Cannot reason about Indonesian equities, MSCI composition, conglomerate groups | Generic stock framework |

### 1.3 Reference Projects Comparison

#### TradingAgents (84.2k ⭐)
- **Strong:** Multi-agent debate (bullish vs bearish researchers), structured decision output, multi-LLM support, persistent decision log
- **Weak:** CLI-only, no executive dashboard, no RAG knowledge system
- **Applicable to Karsa:** Debate mechanism, portfolio manager role, decision log structure

#### Investment-Team (152 ⭐)
- **Strong:** RAG knowledge layer (PgVector), 3-layer context (static/research/memos), 4 team archetypes, deterministic workflow
- **Weak:** Smaller scope, less governance rigor than Karsa
- **Applicable to Karsa:** Knowledge layering, workflow pipeline, agent team coordination patterns

---

## PART 2: DOMAIN REQUIREMENTS FOR CIO DASHBOARD

### 2.1 What a CIO Actually Needs (Not What Developers Think)

#### Executive Summary Layer
A CIO needs **5-second comprehension** of:
- "What are we invested in right now?" → **Portfolio composition + latest changes**
- "What's the most important decision today?" → **Top conviction thesis with rationale**
- "Are we within risk mandates?" → **Traffic light: green/amber/red by risk metric**
- "How did we do yesterday?" → **P&L, alpha vs benchmark, what worked/what didn't**

#### Detailed Analysis Layer
When drilling in, a CIO expects:
- **Stock-level decision cards:**
  - Buy/Hold/Sell/Pass status with conviction (Strong/Medium/Weak)
  - Entry price (historical) + exit price (target) + current price
  - Position size recommendation + mandate compliance flag
  - 3 key reasons in plain English
  - Next review date
- **Risk dashboard:**
  - Sector exposure vs mandate limits
  - Volatility by holding period (1-week, 1-month, 3-month)
  - Beta-adjusted returns
  - Concentration risk (top 5 holdings as % of portfolio)
- **Performance attribution:**
  - P&L decomposition: selection (stock pick), allocation (position sizing), beta (market), residual
  - Win rate by analyst type (fundamentals vs technicals)
  - Backtest performance of this exact strategy

#### Not Helpful to CIO
- ❌ "Agent 7 wrote a 1000-word essay about BBCA"
- ❌ "LLM reasoning trace showing debate steps"
- ❌ "Probability distributions from 5 different models"
- ✅ Instead: "**BUY BBCA at 8,500 IDR, target 9,200 IDR, conviction STRONG** — Dividend yield 3.5% above IHSG, free float improvement post-reclass"

### 2.2 IDX-Specific Context for Karsa

Your expertise in Indonesian equities should be **baked into agent prompts**:

```
MANDATE CONTEXT:
- Indonesian Index (IDX) equities only (BBCA, BBRI, BMRI, ASII, etc.)
- Conglomerate exposure: Prajogo (MBSS, MEDC), Sinarmas (BMNRT), Bakrie (BKSL, BIPI)
- MSCI Indonesia constituents: watch downgrade risk
- Foreign outflow sensitivity: rupiah correlation tracking
- Dividend calendar: ex-date tracking for 58-stock universe

DECISION FRAMEWORK:
- Entry: Based on dividend yield + growth rate + valuation vs historical range
- Exit: Dividend cut, MSCI drop, rupiah weakness > 2% weekly
- Position Size: Kelly criterion on historical volatility (which is high in IDX)
- Conviction Levels: STRONG (3 analyst agreement), MEDIUM (2/3), WEAK (contrarian call)

RESEARCH LIBRARY:
- Sector analyses: Banking (rate sensitivity), Energy (commodity), Technology (FX exposure)
- Company profiles: Historical trading ranges, dividend history, insider trading patterns
```

---

## PART 3: PROPOSED ARCHITECTURE ENHANCEMENTS

### 3.1 Agent Role Expansion (Investment Specialists)

Extend the existing orchestration to include specialized investment agents:

```
ANALYST TEAM (Process in parallel):
├── Fundamentals Analyst
│   ├── Tools: YFinance (financials), SEC Edgar (if US), IDX company reports
│   ├── Outputs: P/E, Price/Book, Dividend Yield, ROE, Free Cash Flow, Growth Rate
│   └── Decision: Intrinsic value estimate + margin of safety

├── Technical Analyst
│   ├── Tools: YFinance (OHLCV), Technical Indicators (RSI, MACD, Bollinger Bands)
│   ├── Outputs: Support/Resistance levels, trend strength, momentum
│   └── Decision: Entry/exit price + holding period estimate

├── Sentiment Analyst
│   ├── Tools: Exa/web search (news), StockTwits API, Reddit parsing
│   ├── Outputs: News sentiment score, retail vs institutional tone
│   └── Decision: Short-term momentum (1-4 week) vs long-term thesis strength

├── Risk Officer
│   ├── Tools: YFinance (volatility), Portfolio manager API
│   ├── Outputs: Position sizing (Kelly criterion), mandate compliance check
│   └── Decision: Maximum position size + red flags (concentration, correlations)

└── Market Context Agent
    ├── Tools: Macro feeds (Fed rates, rupiah FX, commodity prices)
    ├── Outputs: Macro regime (risk-on/risk-off), sector rotation signals
    └── Decision: Portfolio rotation recommendations

RESEARCHER TEAM (Multi-round debate):
├── Bull Researcher
│   ├── Synthesizes: Fundamentals + Technical + Sentiment for case for investment
│   └── Debate: "Here's why we BUY"
└── Bear Researcher
    ├── Synthesizes: Risk, sentiment, macro headwinds, missed catalysts
    └── Debate: "Here's why we PASS or SELL"

EXECUTIVE TEAM:
├── Portfolio Manager
│   ├── Integrates: All researcher inputs + existing positions
│   ├── Decides: BUY (strong/medium), HOLD, SELL (medium/strong), PASS
│   └── Outputs: Investment memo + conviction score

└── Committee Chair (LLM)
    ├── Final reviewer: Checks memo for mandate compliance + logic consistency
    ├── Veto power: Can reject recommendation if red flags exist
    └── Outputs: APPROVED / REVISION NEEDED / REJECTED

```

### 3.2 Three-Layer Knowledge System (Inspired by Investment-Team)

#### Layer 1: Static Context (Prompt Injection)
```
File: docs/investment_context/MANDATE.md
├── Fund size: IDR 10B (example)
├── Allowed universe: IDX-listed, market cap > IDR 5T
├── Sector limits: Finance ≤ 30%, Energy ≤ 20%
├── Concentration: Top 5 holdings ≤ 60% of portfolio
├── Rebalance frequency: Quarterly, or if any position > 30%
├── Holding period: 1-5 years (medium term)
├── Dividend reinvestment: Yes (compounding)
└── Leverage: Not allowed

File: docs/investment_context/RISK_POLICY.md
├── Max volatility (annual): 22%
├── Max drawdown tolerance: 15%
├── Beta limits: 0.8 - 1.3 relative to IHSG
├── Correlation thresholds: Sector pairs < 0.7
└── Liquidity: Position must be closeable in < 5 trading days

File: docs/investment_context/DECISION_PROCESS.md
├── Step 1: Market context check (is environment suitable?)
├── Step 2: Fundamental + Technical + Sentiment in parallel
├── Step 3: Debate (bull vs bear, 1-2 rounds)
├── Step 4: Portfolio manager synthesis
├── Step 5: Risk officer veto/approval
├── Step 6: Memo writing + historic decision log update
├── Step 7: Committee chair final sign-off
└── Step 8: Action (if approved: execute trade, else: revisit next month)
```

#### Layer 2: Research Library (RAG via PgVector)
```
PostgreSQL + pgvector extension:

TABLE research_documents (
  id UUID PRIMARY KEY,
  title TEXT,
  ticker VARCHAR(10),
  doc_type ENUM('sector_analysis', 'company_profile', 'market_thesis'),
  content TEXT,
  embedding vector(1536),  -- OpenAI text-embedding-3-small
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  metadata JSONB  -- {sector: "Banking", market_cap: "5T IDR", ...}
);

EXAMPLE DOCUMENTS:
- "Banking Sector Indonesia 2026: Interest Rate Sensitivity Analysis"
  → Used when analyzing BBCA, BBRI, BMRI
  
- "ASII: Astra International - Automotive OEM Exposure"
  → Linked: automotive cyclical downturn, FX sensitivity, dividend history
  
- "Conglomerate Groups: Prajogo, Sinarmas, Bakrie Cross-Holdings"
  → Cross-reference when one holding affects others

QUERY PATTERN:
Analyst asks: "What does our research say about banking sector rotation in IDX?"
RAG response: Top 3 documents ordered by relevance + excerpts
Analyst integrates: Uses historical analysis + current market data for decision
```

#### Layer 3: Memo Archive (File-Based + Database)
```
Directory: docs/investment_memos/

FILE: BBCA_2026_Q2_BUY.md
---
# Investment Memo: BBCA (Bank Central Asia)
Date: 2026-06-15
Ticker: BBCA
Decision: BUY
Conviction: STRONG
Current Price: 8,650 IDR
Entry Price: 8,500-8,700 IDR
Exit Price (Target): 9,200 IDR (6-month)

## Thesis (3-4 sentences)
BBCA offers 3.5% dividend yield + 8% EPS growth. Interest rate hold supports margins. 
Free-float improvement post-index reclass removes overhang. Fundamentals strong, technicals constructive.

## Key Metrics
- P/E: 15.8x (vs 5-year avg 16.2x) → slight undervaluation
- Dividend Yield: 3.5% (tax-deferred for holding > 1 year)
- ROE: 18.2% (above WACC of 9%)
- Free Cash Flow Yield: 2.1%

## Risks
- ⚠️ Interest rate cuts (Fed tightening spillover)
- ⚠️ MSCI downgrade (float requirement tightens)
- ⚠️ Conglomerate cross-defaults (if Sinarmas group stress)

## Decision Log
Fundamental Score: 8/10  (analyst: AI_Fundamentals_Agent)
Technical Score: 7/10   (analyst: AI_Technical_Agent)
Sentiment Score: 6/10   (analyst: AI_Sentiment_Agent)
Risk Assessment: PASS   (analyst: AI_Risk_Officer)
Bull Case: Dividend + growth + reclass catalyst
Bear Case: Macro headwinds, MSCI risk
Portfolio Mgr Decision: BUY (2.5% position, 10-unit order)
Committee Approval: ✅ APPROVED

## Follow-up
- Next review: 2026-09-15
- Stop-loss: 8,200 IDR (if technical support breaks)
- Target review: On ex-date for dividends (typically Q2, Q4)

---

MEMO DATABASE TABLE:
TABLE investment_memos (
  id UUID PRIMARY KEY,
  ticker VARCHAR(10),
  decision_date DATE,
  decision ENUM('BUY', 'HOLD', 'SELL', 'PASS'),
  conviction ENUM('STRONG', 'MEDIUM', 'WEAK'),
  entry_price DECIMAL(12,2),
  exit_price DECIMAL(12,2),
  thesis TEXT,
  key_metrics JSONB,
  realized_return DECIMAL(8,4),  -- Filled after position closed
  alpha_vs_ihsg DECIMAL(8,4),    -- Alpha decomposition
  created_by VARCHAR(100),        -- AI agent name
  updated_by VARCHAR(100),
  status ENUM('active', 'closed', 'invalidated'),
  created_at TIMESTAMP,
  closed_at TIMESTAMP
);

USAGE IN AGENTS:
- On next BBCA decision, agent retrieves all past BBCA memos
- Agent compares: "Last time we bought at 8,500, target 9,200, took 6 months"
- Agent checks: "Did it hit target? What actually happened?"
- Agent learns: "Our entry/exit bands are accurate within ±200 IDR"
- Agent updates: Uses this historical accuracy in new conviction scoring
```

### 3.3 Investment Workflow Pipeline

```
TRIGGER: User asks "Should we invest in ASII?" or scheduled daily review

PHASE 1: PARALLEL ANALYSIS (2-3 minutes)
├─ Fundamental Analyst
│  ├─ YFinance: ASII last 10 years (P/E, dividend, revenue growth)
│  ├─ IDX filings: Latest quarterly report, insider trading
│  ├─ Output: Valuation score + intrinsic value range
│  └─ Confidence: 8/10 (historical data is reliable)
│
├─ Technical Analyst
│  ├─ YFinance OHLCV: Daily closes, intraday levels
│  ├─ Indicators: RSI (30-70), MACD (trend), Bollinger (volatility bands)
│  ├─ Output: Entry/exit levels + trend strength
│  └─ Confidence: 6/10 (IDX is more volatile than developed markets)
│
├─ Sentiment Analyst
│  ├─ Web search: Recent news (mergers, guidance cuts, regulatory)
│  ├─ Retail chatter: Twitter, StockTwits (if available for IDX)
│  ├─ Output: Short-term momentum + catalyst awareness
│  └─ Confidence: 5/10 (Indonesian sentiment data is sparse)
│
└─ Market Context Agent
   ├─ Macro feeds: Rupiah FX, BIS (2-year, 10-year), commodity prices
   ├─ Sector rotation: Banking rates, Energy crude, Tech FX
   ├─ Output: Risk-on/risk-off regime + sector rotation signal
   └─ Confidence: 7/10 (macro data is publicly available)

PHASE 2: RESEARCHER DEBATE (1-2 rounds)
├─ Bull Researcher reads all 4 analysis outputs above
│  ├─ Synthesizes: "Here's the case for BUY at this price"
│  ├─ Conviction: STRONG if 3/4 analysts agree positively
│  └─ Output: Bull memo (500 words max)
│
└─ Bear Researcher reads same outputs
   ├─ Synthesizes: "Here's the case for caution / PASS"
   ├─ Flags: What could go wrong? Missing catalysts?
   └─ Output: Bear memo (500 words max)

PHASE 3: PORTFOLIO MANAGER SYNTHESIS
├─ Integration:
│  ├─ Review current ASII position (if any)
│  ├─ Check mandate constraints (sector allocation, concentration)
│  ├─ Compare vs other opportunities in opportunity set
│  ├─ Calculate position sizing using Kelly criterion
│  └─ Final decision: BUY (strong/medium) / HOLD / SELL (medium/strong) / PASS
│
└─ Output: Investment memo (above format)

PHASE 4: RISK OFFICER VETO
├─ Checklist:
│  ├─ ☐ Position size ≤ 3% per stock
│  ├─ ☐ Sector total ≤ 30% (if Banking) or ≤ 20% (if Energy)
│  ├─ ☐ Concentration (top 5) ≤ 60%
│  ├─ ☐ Liquidity: Can close this in 5 trading days?
│  ├─ ☐ Correlation: New position doesn't add beta > limit
│  └─ ☐ Downside: Max loss ≤ 15% of position (stop-loss respected)
│
├─ Decision:
│  ├─ ✅ APPROVED — Execute recommendation
│  ├─ ⚠️ REVISION NEEDED — Ask PM to reduce size / adjust timing
│  └─ ❌ REJECTED — Explain why, file for later review
│
└─ Output: Risk assessment attached to memo

PHASE 5: COMMITTEE CHAIR FINAL REVIEW
├─ Review: Entire memo chain above
├─ Check: Logic consistency, mandate compliance, no hallucinations
├─ Possible actions:
│  ├─ ✅ APPROVED → Ready for execution
│  ├─ ⏳ HOLD → Ask for re-analysis next week
│  ├─ 🔄 REVISE → Go back to Portfolio Manager
│  └─ ❌ REJECTED → File decision + reason
│
└─ Output: Final approved memo (goes into Layer 3 archive)

PHASE 6: EXECUTION (If APPROVED)
├─ Trade execution layer (stub for now):
│  ├─ Order construction: Entry price, size, order type (limit/market)
│  ├─ Risk checks: Margin available, liquidity available
│  ├─ Audit: Log who approved, timestamp, all parameters
│  └─ Confirmation: Send to broker API (when production)
│
└─ Update: Post-execution memo with fill details

PHASE 7: MONITORING
├─ Daily checks:
│  ├─ Current price vs entry/exit targets
│  ├─ Fundamental trigger events (dividend cut, guidance, regulatory)
│  ├─ Technical breaks (support breaks → sell signal)
│  └─ Macro changes (rupiah crash, rate cut, sector rotation)
│
├─ If trigger hit:
│  ├─ Generate re-analysis on target stock
│  ├─ Update conviction + price target
│  ├─ Execute exit if risk limit breached
│  └─ Close memo + record actual return
│
└─ Archive: Realized return vs target, alpha decomposition
```

### 3.4 CIO Dashboard Component Hierarchy

```
LAYOUT: 3-tier pyramid (summary → analysis → detail)

TIER 1: EXECUTIVE SUMMARY (Above the fold, 30 seconds)
├─ Portfolio Status Card
│  ├─ Current NAV: IDR 10.2B (+2.1% WTD, +15.3% YTD)
│  ├─ Sharpe Ratio: 1.8 (vs IHSG 1.2)
│  ├─ Max Drawdown YTD: 8.2% (within 15% limit) ✅
│  ├─ Active Holdings: 12 stocks
│  └─ Cash: 5% (available for deployment)
│
├─ Risk Traffic Light
│  ├─ Volatility: 18% annual (within 22% limit) 🟢
│  ├─ Beta (IHSG): 1.05 (within 0.8-1.3) 🟢
│  ├─ Concentration (top 5): 52% (within 60%) 🟢
│  ├─ Sector allocation: Banking 28% (within 30%) 🟢
│  └─ Liquidity: All positions closeable in 3 days 🟢
│
└─ Today's Decisions
   ├─ New BUY: MEDC (Medco) - STRONG conviction - IDR 285-300 target
   ├─ Position UP: ASII (Astra) - Add 0.5% more on dip
   ├─ Alert: BKSL (Bakrie) - Dividend cut risk flagged, reviewing exit
   └─ Monitor: IPVF (Inditrade) - PASS decision, revisit Q3

TIER 2: DECISION & ANALYSIS CARDS (30-60 second drill-down)
├─ Stock Decision Card (repeated for each holding/candidate)
│  ├─ Ticker: BBCA (Bank Central Asia)
│  ├─ Status: HOLD (was BUY from memo dated 2026-04-15)
│  ├─ Current Price: 8,750 IDR
│  │  ├─ Entry Price (memo): 8,500 IDR → ✅ Target hit 27% of way to 9,200
│  │  ├─ Target Price: 9,200 IDR (6-month)
│  │  └─ Stop Loss: 8,200 IDR
│  ├─ Position Size: 2.5% of portfolio (12,000 shares)
│  ├─ Conviction Level: STRONG (88% confidence)
│  │  ├─ Fundamental score: 8/10 (P/E undervalued, ROE 18%)
│  │  ├─ Technical score: 7/10 (above 50-day MA, RSI 55)
│  │  ├─ Sentiment score: 6/10 (neutral news, some retail selling)
│  │  └─ Risk score: PASS (position size OK, no mandate breach)
│  ├─ Performance This Holding:
│  │  ├─ Current Return: +2.9% since entry
│  │  ├─ Next Catalyst: Dividend ex-date 2026-08-01 (yield 3.5%)
│  │  └─ Risk Factor: MSCI downgrade risk if free-float < 15%
│  │
│  └─ Actions:
│     ├─ 🟢 Hold (No action today)
│     ├─ 📈 Add more (if breaks above 8,900)
│     ├─ 📉 Reduce (if breaks below 8,200)
│     └─ 📋 Read Full Memo (opens decision doc)
│
├─ Risk Heatmap
│  ├─ Sector Allocation vs Mandate:
│  │  ├─ Finance: 28% of 30% limit (93% utilized) 🟠
│  │  ├─ Energy: 15% of 20% limit (75% utilized) 🟢
│  │  ├─ Tech: 12% of no limit 🟢
│  │  ├─ Consumer: 18% of 25% limit (72% utilized) 🟢
│  │  └─ Other: 27% 🟢
│  │
│  ├─ Holding Correlation Matrix:
│  │  ├─ BBCA-BBRI: 0.72 (high) — consider reducing one
│  │  ├─ ASII-GGRM: 0.15 (low) — good diversification
│  │  └─ ADRO-INDY: 0.68 (high) — energy sector concentration
│  │
│  └─ Top 5 Holdings (Concentration Risk):
│     ├─ BBCA: 12.5%
│     ├─ ASII: 10.2%
│     ├─ MEDC: 8.1%
│     ├─ BBRI: 11.3%
│     └─ GGRM: 9.9% → Total 52% (within 60% limit) ✅
│
└─ Performance Attribution (Today + MTD + YTD)
   ├─ P&L Breakdown:
   │  ├─ Selection (stock picking): +8.2% YTD 📈
   │  ├─ Allocation (position sizing): +3.1% YTD 📈
   │  ├─ Beta (market exposure): +2.4% YTD 📈
   │  └─ Residual (fees, friction): -0.2% YTD 📉
   │
   ├─ Win Rate:
   │  ├─ Fundamental-based picks: 68% win rate (17/25)
   │  ├─ Technical-based picks: 55% win rate (11/20)
   │  ├─ Sentiment-based contrarian: 42% win rate (5/12)
   │  └─ Macro calls: 71% win rate (15/21)
   │
   └─ Model Performance:
      ├─ Backtested Sharpe (this strategy): 1.9
      ├─ Actual Sharpe YTD: 1.8 (tracking well)
      ├─ Model accuracy: 73% (buy recommendations hit target within 6 months)
      └─ Max drawdown prediction error: ±2.1% (vs actual)

TIER 3: DETAILED DECISION DOCUMENTS
├─ Full Investment Memo (MD file)
├─ Analyst Debate Transcript (Bull vs Bear)
├─ Historical Decision Log (past 3 years on same stock)
├─ Risk Assessment Checklist (with veto notes)
└─ Execution Log (entry price, fees, slippage, actual fill)

NAVIGATION:
Dashboard → Click on any decision card → Full memo + analyst debate + historical context
```

### 3.5 Database Schema Expansion

```sql
-- Layer 1: Agent Decisions (Timestamped, immutable)
CREATE TABLE agent_decisions (
  id UUID PRIMARY KEY,
  analyst_type VARCHAR(50),  -- 'fundamental', 'technical', 'sentiment', 'risk', 'macro'
  ticker VARCHAR(10),
  decision_date DATE,
  analysis_date TIMESTAMP,
  score_0_to_10 DECIMAL(3,1),
  output_text TEXT,
  confidence DECIMAL(3,1),
  tools_used JSONB,  -- ['YFinance', 'web_search', 'exa']
  model_version VARCHAR(20),
  created_at TIMESTAMP,
  UNIQUE(analyst_type, ticker, decision_date)
);

-- Layer 2: Debate & Synthesis
CREATE TABLE debate_sessions (
  id UUID PRIMARY KEY,
  ticker VARCHAR(10),
  session_date DATE,
  bull_memo TEXT,
  bear_memo TEXT,
  bull_analyst_id UUID,
  bear_analyst_id UUID,
  rounds INTEGER,
  final_conviction ENUM('STRONG', 'MEDIUM', 'WEAK'),
  created_at TIMESTAMP
);

-- Layer 3: Portfolio Decisions (Approved memos)
CREATE TABLE investment_decisions (
  id UUID PRIMARY KEY,
  ticker VARCHAR(10),
  decision_date DATE,
  decision ENUM('BUY', 'HOLD', 'SELL', 'PASS'),
  conviction ENUM('STRONG', 'MEDIUM', 'WEAK'),
  entry_price DECIMAL(12,4),
  exit_target DECIMAL(12,4),
  position_size_pct DECIMAL(5,2),
  thesis TEXT,
  key_metrics JSONB,  -- {pe: 16.5, dividend_yield: 3.5, roe: 18.2, ...}
  risk_flags JSONB,  -- {msci_float_risk: true, conglomerate_stress: false, ...}
  pm_id VARCHAR(100),
  risk_officer_id VARCHAR(100),
  committee_chair_id VARCHAR(100),
  status ENUM('approved', 'rejected', 'revision_needed'),
  created_at TIMESTAMP,
  approved_at TIMESTAMP
);

-- Layer 4: Execution & Performance
CREATE TABLE position_executions (
  id UUID PRIMARY KEY,
  decision_id UUID REFERENCES investment_decisions(id),
  ticker VARCHAR(10),
  action ENUM('buy', 'sell', 'reduce', 'add'),
  quantity INTEGER,
  execution_price DECIMAL(12,4),
  execution_date DATE,
  order_id VARCHAR(50),  -- Broker order ID (when live)
  commission DECIMAL(10,4),
  executed_at TIMESTAMP
);

CREATE TABLE closed_positions (
  id UUID PRIMARY KEY,
  decision_id UUID REFERENCES investment_decisions(id),
  ticker VARCHAR(10),
  entry_date DATE,
  entry_price DECIMAL(12,4),
  exit_date DATE,
  exit_price DECIMAL(12,4),
  quantity INTEGER,
  realized_return_pct DECIMAL(8,4),  -- Realized P&L %
  alpha_vs_ihsg DECIMAL(8,4),         -- Excess return vs benchmark
  holding_period_days INTEGER,
  memo_id VARCHAR(100),
  created_at TIMESTAMP
);

-- Layer 5: Knowledge & Memory
CREATE TABLE research_documents (
  id UUID PRIMARY KEY,
  title TEXT,
  ticker VARCHAR(10),
  sector VARCHAR(50),
  doc_type ENUM('sector_analysis', 'company_profile', 'thesis', 'macro_view'),
  content TEXT,
  embedding vector(1536),  -- OpenAI text-embedding-3-small
  created_by VARCHAR(100),
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  metadata JSONB
);

-- Layer 6: Audit Trail (Everything)
CREATE TABLE audit_log (
  id UUID PRIMARY KEY,
  action VARCHAR(100),  -- 'decision_created', 'decision_approved', 'position_executed', etc.
  actor VARCHAR(100),   -- AI agent name or human user ID
  ticker VARCHAR(10),
  before_state JSONB,   -- Full object before change (for diff tracking)
  after_state JSONB,    -- Full object after change
  reason TEXT,          -- Why was this action taken?
  created_at TIMESTAMP,
  INDEX(ticker, created_at)  -- Queries: "Show all actions on BBCA in last 30 days"
);

-- Layer 7: Performance Attribution (Daily snapshots)
CREATE TABLE daily_performance (
  id UUID PRIMARY KEY,
  date DATE UNIQUE,
  nav DECIMAL(15,2),
  nav_pct_change DECIMAL(8,4),
  ihsg_close DECIMAL(10,2),
  ihsg_pct_change DECIMAL(8,4),
  alpha DECIMAL(8,4),           -- Our return minus IHSG return
  selection_contribution DECIMAL(8,4),  -- From stock picking
  allocation_contribution DECIMAL(8,4), -- From position sizing
  sharpe_ytd DECIMAL(5,2),
  max_drawdown_ytd DECIMAL(8,4),
  created_at TIMESTAMP
);
```

---

## PART 4: IMPLEMENTATION ROADMAP

### Phase 1: Core Agent Architecture (Sprint 51-52, 2-3 weeks)

**Deliverables:**
1. Create specialized agent modules in `src/agents/`:
   - `fundamentals_analyst.py` — Fetch YFinance, compute ratios
   - `technical_analyst.py` — RSI, MACD, Bollinger bands
   - `sentiment_analyst.py` — Web search + news parsing
   - `risk_officer.py` — Mandate checks, Kelly sizing
   - `market_context.py` — Macro feeds

2. Implement `src/orchestration/investment_workflow.py`:
   - Parallel analyst execution (asyncio)
   - Debate mechanism (bull vs bear synthesis)
   - Portfolio manager decision layer
   - Risk officer veto checks

3. Create `docs/investment_context/` directory:
   - `MANDATE.md` (fund rules)
   - `RISK_POLICY.md` (position/sector limits)
   - `IDX_KNOWLEDGE.md` (conglomerate groups, dividend calendar)

4. Write tests:
   - Unit: Each agent produces valid output (no hallucinations)
   - Integration: Workflow runs end-to-end on BBCA in < 5 min
   - Behavioral: Decision memo has required fields

**Success Criteria:**
- ✅ Run `python -m src.orchestration.run_investment_workflow BBCA` → generates valid memo in < 5 minutes
- ✅ All 4 analysts agree on a stock → conviction STRONG (test with historical data)
- ✅ Risk officer correctly flags mandate violations
- ✅ Memo contains entry/exit prices + conviction + thesis

---

### Phase 2: Knowledge & Memory Systems (Sprint 52-53, 2 weeks)

**Deliverables:**
1. Set up PostgreSQL + pgvector:
   - Run `docker-compose up` → PostgreSQL + pgvector extension ready
   - Migration: `alembic/versions/001_create_knowledge_tables.py`

2. Implement `src/knowledge/`:
   - `knowledge_loader.py` — Load research docs from `docs/research/` into PgVector
   - `knowledge_retriever.py` — RAG query: "What does our research say about BBCA?"
   - `memo_archiver.py` — Store approved memos in DB + filesystem

3. Integrate into agents:
   - Fundamentals analyst: RAG query "BBCA historical analysis" → use as context
   - Decision memo: Auto-generate from structured agent outputs

4. Test RAG:
   - Load 10 research docs on banking sector
   - Query: "Interest rate sensitivity IDX banks"
   - Verify top results are relevant

**Success Criteria:**
- ✅ `curl http://localhost:8000/api/knowledge/search?q=BBCA` → returns top 3 relevant docs
- ✅ Agent uses retrieved docs in decision reasoning (visible in memo)
- ✅ Memo archive searchable: "Show all BBCA decisions since 2025"
- ✅ Realized returns logged: "BBCA entry 8,500 → exit 9,200, return +8.2%"

---

### Phase 3: CIO Dashboard Frontend (Sprint 53-54, 3 weeks)

**Deliverables:**
1. New Next.js workspace in `karsa-web/src/app/cio-dashboard/`:
   - `/` → Executive summary (portfolio status, risk, today's decisions)
   - `/holdings` → Table of all 12 holdings with decision cards
   - `/analysis/[ticker]` → Drill into single stock (memo, debate, historical)
   - `/risk` → Heatmap, correlation matrix, sector allocation
   - `/performance` → Attribution, win rates, backtest comparison

2. Components (shadcn/ui + Recharts):
   - `<PortfolioStatusCard />` — NAV, Sharpe, max drawdown, 4 KPIs
   - `<StockDecisionCard />` — Ticker, price, conviction, actions
   - `<RiskTrafficLight />` — Green/amber/red for 6 metrics
   - `<SectorAllocationChart />` — Stacked bar vs mandate limits
   - `<CorrelationHeatmap />` — AG Grid heatmap of pairwise correlations
   - `<PerformanceAttribution />` — Waterfall: selection + allocation + beta + fees
   - `<ConvictionGauge />` — Radial gauge (0-100) for stock conviction

3. Data integration:
   - TanStack Query hooks:
     - `usePortfolioSummary()` → API `/api/portfolio/summary`
     - `useStockDecision(ticker)` → API `/api/decisions/{ticker}/latest`
     - `usePerformanceAttribution(period)` → API `/api/performance/attribution?period=ytd`
   - Error boundaries: Graceful degradation if memo data missing

4. TypeScript types:
   - `PortfolioSummary`, `StockDecision`, `RiskAssessment`, `PerformanceMetrics`
   - Mappers: API DTO → Dashboard ViewModel (defensive coalescing)

**Success Criteria:**
- ✅ Dashboard loads in < 2s (static export, cached API responses)
- ✅ Click "BBCA" → opens full memo + debate transcript + historical decisions
- ✅ Risk traffic light correctly shows red if sector > limit
- ✅ Performance waterfall sums to actual YTD return ±0.1%
- ✅ Works offline (static export, last API snapshot cached)

---

### Phase 4: Governance & Audit Integration (Sprint 54-55, 2 weeks)

**Deliverables:**
1. API routes in `src/api/`:
   - `POST /api/decisions` — Create decision (agent output)
   - `POST /api/decisions/{id}/approve` — PM approval (triggers memo writing)
   - `POST /api/decisions/{id}/veto` — Risk officer veto + revision request
   - `GET /api/decisions/{ticker}/history` — All past decisions on stock
   - `GET /api/audit-log?ticker=BBCA` — All actions on a stock

2. Audit table population:
   - Every decision creation/approval/veto/execution logged
   - Query: "Who approved this trade? When? With what reasoning?"
   - Export: Full audit trail as CSV for compliance

3. Memo generation workflow:
   - Agent outputs → `POST /api/memos` → stored in DB + filesystem (`docs/investment_memos/BBCA_2026_Q2_BUY.md`)
   - Lookup past memo on same ticker → compute realized return
   - Update memo with "Last BBCA position: returned +8.2%, hit target in 5 months"

4. Test compliance:
   - Scenario: "Risk officer rejects BUY because sector limit would exceed 30%"
   - Verify: Memo marked REJECTED, PM notified, audit logged
   - Re-analysis: PM reduces position size to 2% instead of 3%, resubmits → APPROVED

**Success Criteria:**
- ✅ Full audit trail: "BBCA decision approved by PM at 14:32 on 2026-06-15"
- ✅ Realized return comparison: "Previous BBCA memo target 9,200, actual 9,210, error ±0.1%"
- ✅ Compliance report: "All BUYs this month maintained mandate compliance ✅"

---

### Phase 5: IDX Domain Enhancement (Sprint 55-56, 1-2 weeks)

**Deliverables:**
1. Research library seeding:
   - Create 10-15 markdown files in `docs/research/`:
     - `banking_sector_2026.md` — Interest rate sensitivity
     - `conglomerate_groups.md` — Prajogo, Sinarmas, Bakrie cross-holdings
     - `msci_rebalance_risk.md` — Free-float methodology changes
     - `dividend_calendar_2026.md` — Ex-dates for 58-stock universe
   - Load into PgVector via `python -m src.knowledge.knowledge_loader`

2. Agent prompt engineering:
   - Update system prompts to reference mandate context:
     ```
     You are an investment analyst for an IDX-focused fund.
     Fund mandate: 
     - Holdings: Indonesian equities only (BBCA, BBRI, ASII, ...)
     - Sector limits: Finance ≤ 30%, Energy ≤ 20%
     - Holding period: 1-5 years
     
     Recent IDX context:
     {MANDATE_CONTEXT}
     
     Relevant research from our library:
     {RAG_RETRIEVED_DOCS}
     ```

3. Dashboard IDX-specific enhancements:
   - Dividend calendar widget: "Next ex-dates by month"
   - MSCI free-float tracker: "Current % to critical 15% threshold"
   - Conglomerate exposure: "Total Prajogo group: 15.2% of portfolio"
   - Macro dashboard: "Rupiah vs USD, BIS rates, commodity prices"

4. Backtest on historical IDX trades:
   - Pick 5 BBCA trades from 2024-2025
   - Verify memo targets were accurate
   - Compute model accuracy: "Target ±200 IDR"

**Success Criteria:**
- ✅ RAG query "Conglomerate risk" → returns doc on cross-holdings
- ✅ Agent memo includes: "MSCI float risk flagged due to reclass in Q4"
- ✅ Dividend calendar shows: "BBCA ex-date 2026-08-01, yield 3.5%"
- ✅ Backtest accuracy: 73% of BUY recommendations hit target within 6 months

---

## PART 5: CRITICAL SUCCESS FACTORS

### 5.1 Don't Build These (Anti-Patterns)

❌ **Generic agent that writes 1000-word essays about why to buy a stock**
→ CIO needs 100-word summary with entry/exit/conviction. Essays go to research library.

❌ **Dashboard with 50 metrics and no clear call-to-action**
→ Start with 5-7 critical metrics. Add detail on drill-down.

❌ **Agents that never check their own accuracy**
→ Every closed position must log realized return vs memo target.
→ Use this to adjust conviction scoring (if targets were wrong, lower confidence).

❌ **No audit trail**
→ Every recommendation must be traceable: who decided, why, when approved.

❌ **Manual data entry for decisions**
→ Workflow must be: Agent outputs → DB → Memo file → Dashboard (all automated).

### 5.2 Build These (Success Patterns)

✅ **3-layer knowledge** (static context → research library → memo archive)
→ Agents learn from past mistakes. Decisions improve over time.

✅ **Debate mechanism** (bull + bear synthesis)
→ Catches one-sided analysis. Conviction scoring becomes meaningful.

✅ **Risk officer veto**
→ Prevents mandate breaches before execution. Governance by design, not audit.

✅ **CIO-friendly metrics** (entry/exit prices, conviction, win rate)
→ Executive decision in 30 seconds. Details available on drill-down.

✅ **Realized return logging**
→ Close the feedback loop. "We said 9,200, actual was 9,210. Model accuracy: 99.9%"

✅ **IDX domain context in every agent**
→ Agents understand conglomerate groups, dividend calendars, MSCI float risk.

### 5.3 Metrics That Matter

| Metric | Target | How to Measure |
|--------|--------|-----------------|
| **Agent Decision Quality** | 73%+ of BUY memo targets hit within 6 months | Backtester: closed_positions.realized_return vs memo.exit_target |
| **Governance Coverage** | 100% of decisions have audit trail | Query: `audit_log WHERE action='decision_approved'` should match `investment_decisions` count |
| **CIO Dashboard Load Time** | < 2 seconds (static export) | Lighthouse audit + real user monitoring |
| **Knowledge Freshness** | Latest memo on every stock ≤ 30 days old | Query: `MAX(decision_date) BY ticker` — all < 30 days |
| **Risk Mandate Compliance** | 100% of positions respect sector/concentration limits | Daily batch: Compare portfolio vs mandate, alert if any violation |
| **Debate Conviction Accuracy** | STRONG decisions win rate > MEDIUM > WEAK | Backtest: conviction_level correlated with realized_return |

---

## PART 6: REFERENCE ARCHITECTURE DIAGRAMS

### Dataflow: Decision → Execution → Monitoring

```
┌─────────────────────────────────────────────────────────┐
│ USER QUERY: "Should we invest in ASII?"                 │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────▼────────────┐
         │ PARALLEL ANALYSIS (2m) │
         ├───────────┬──────────┬─────────────┐
         │           │          │             │
    ┌────▼───┐  ┌───▼──┐  ┌───▼──┐  ┌──────▼──┐
    │ Fundl. │  │Tech. │  │ Sent.│  │ Market  │
    │ +2.5m  │  │ 1m   │  │ 2m   │  │ 1m      │
    └────┬───┘  └───┬──┘  └───┬──┘  └──────┬──┘
         │          │         │           │
         │          └─────────▼───────────┘
         │                    │
    ┌────▼────────────────────▼────────────┐
    │ DEBATE SYNTHESIS (1m, 1-2 rounds)    │
    │ Bull Researcher: BUY case             │
    │ Bear Researcher: PASS case            │
    │ → Final conviction: MEDIUM            │
    └────┬─────────────────────────────────┘
         │
    ┌────▼─────────────────────────────────┐
    │ PORTFOLIO MANAGER (2m)                │
    │ - Check: Current ASII position?       │
    │ - Size: Kelly criterion → 2.5%        │
    │ - Memo: Structured decision output    │
    │ → Decision: BUY ASII at 6,800 IDR     │
    └────┬─────────────────────────────────┘
         │
    ┌────▼─────────────────────────────────┐
    │ RISK OFFICER VETO (30s)               │
    │ ☑ Position size OK (2.5% < 3% limit) │
    │ ☑ Sector OK (Tech 12% < no limit)    │
    │ ☑ Concentration OK (top 5 at 52%)    │
    │ → Approval: APPROVED                  │
    └────┬─────────────────────────────────┘
         │
    ┌────▼─────────────────────────────────┐
    │ COMMITTEE CHAIR FINAL REVIEW (1m)     │
    │ - Read full memo chain                │
    │ - Check logic consistency             │
    │ → Final: APPROVED ✅                  │
    └────┬─────────────────────────────────┘
         │
         ├─────────────────────────────────┐
         │                                 │
    ┌────▼──────────────┐      ┌──────────▼──┐
    │ EXECUTION LAYER   │      │ ARCHIVE     │
    │ (When live)       │      │ - Memo file │
    │ - Order: BUY      │      │ - DB entry  │
    │   ASII 1,000 u    │      │ - Audit log │
    │   at 6,800 IDR    │      │             │
    │ - Fill: 6,785-... │      └──────────────┘
    └────┬──────────────┘
         │
    ┌────▼──────────────────────────────────┐
    │ MONITORING (Daily)                     │
    │ - Current ASII: 6,920 IDR (+2%)       │
    │ - Target: 7,300 IDR (6-month)         │
    │ - Stop loss: 6,500 IDR (if breached)  │
    │ - Next review: 2026-09-15              │
    └────────────────────────────────────────┘
    
    [Every decision is logged, every return is tracked, every memo is archived]
```

---

## PART 7: TESTING STRATEGY

### Behavioral Tests (Investment Domain)

```python
# tests/test_investment_workflow.py

def test_bbca_decision_workflow():
    """End-to-end: BBCA analysis → memo → approval"""
    # Setup
    ticker = "BBCA"
    current_price = 8650
    
    # Run workflow
    result = run_investment_workflow(ticker)
    
    # Assert decision memo has required fields
    assert result.memo.ticker == ticker
    assert result.memo.decision in ['BUY', 'HOLD', 'SELL', 'PASS']
    assert 0 <= result.memo.conviction_score <= 10
    assert result.memo.entry_price > 0
    assert result.memo.exit_target > result.memo.entry_price
    assert len(result.memo.thesis) > 100  # Non-trivial reasoning
    assert result.memo.key_metrics['pe_ratio'] > 0
    assert 'dividend_yield' in result.memo.key_metrics
    
    # Workflow time < 5 minutes
    assert result.execution_time_seconds < 300

def test_risk_officer_veto():
    """Risk officer rejects decision that violates mandate"""
    # Scenario: position size would exceed 3%
    memo = {
        'ticker': 'ASII',
        'decision': 'BUY',
        'proposed_position_pct': 3.5,  # Exceeds 3% limit
    }
    
    result = risk_officer.check(memo, mandate)
    
    assert result.approved == False
    assert "position size" in result.rejection_reason.lower()
    assert result.suggestion == "reduce position to ≤ 3%"

def test_realized_return_accuracy():
    """Past memo targets vs actual returns"""
    # Load historical BBCA decisions
    past_memos = load_past_memos('BBCA', limit=5)
    
    accuracy_errors = []
    for memo in past_memos:
        if memo.status == 'closed':
            target_error_pct = abs(
                memo.exit_target - memo.realized_exit_price
            ) / memo.realized_exit_price * 100
            accuracy_errors.append(target_error_pct)
    
    mean_error = np.mean(accuracy_errors)
    assert mean_error < 5.0  # Targets within ±5% on average
    assert np.std(accuracy_errors) < 10.0  # Consistency

def test_rag_knowledge_retrieval():
    """Research library query returns relevant docs"""
    query = "ASII automotive sector cyclical downturn"
    results = knowledge.search(query, top_k=3)
    
    assert len(results) == 3
    assert results[0].relevance_score > 0.7
    assert 'automotive' in results[0].content.lower()
    assert results[0].ticker == 'ASII' or results[0].sector == 'auto'

def test_conviction_calibration():
    """Conviction levels (STRONG/MEDIUM/WEAK) predict win rate"""
    # Backtest: Group past decisions by conviction level
    strong_decisions = load_decisions(conviction='STRONG')
    medium_decisions = load_decisions(conviction='MEDIUM')
    weak_decisions = load_decisions(conviction='WEAK')
    
    strong_win_rate = compute_win_rate(strong_decisions)
    medium_win_rate = compute_win_rate(medium_decisions)
    weak_win_rate = compute_win_rate(weak_decisions)
    
    # Conviction should correlate with accuracy
    assert strong_win_rate > medium_win_rate > weak_win_rate
    assert strong_win_rate > 0.65  # STRONG decisions win >65% of time
```

### Load & Performance Tests

```python
# tests/test_performance.py

def test_dashboard_load_time():
    """CIO dashboard renders in < 2 seconds"""
    import time
    
    start = time.time()
    response = client.get('/api/cio-dashboard/summary')
    elapsed = time.time() - start
    
    assert response.status_code == 200
    assert elapsed < 2.0  # milliseconds
    assert 'portfolio_nav' in response.json()

def test_concurrent_analysts():
    """4 analysts run in parallel in < 3 minutes"""
    import asyncio
    
    start = time.time()
    results = asyncio.run(run_all_analysts('BBCA'))
    elapsed = time.time() - start
    
    assert len(results) == 4  # All 4 analysts completed
    assert elapsed < 180  # < 3 minutes
    assert all(r.score > 0 for r in results)

def test_memo_archive_query():
    """Query 1000 past memos, return results in < 1s"""
    # Seed 1000 historical memos
    seed_historical_memos(count=1000)
    
    start = time.time()
    results = load_past_memos('BBCA', limit=10)
    elapsed = time.time() - start
    
    assert len(results) <= 10
    assert elapsed < 1.0  # < 1 second
```

---

## PART 8: DEPLOYMENT CHECKLIST

### Pre-Production

- [ ] Docker images built for all services (backend, frontend, postgres)
- [ ] Environment variables documented (`.env.example`)
- [ ] Database migrations tested (Alembic up/down)
- [ ] API rate limiting in place (investors, 100 reqs/minute)
- [ ] Authentication enabled (CIO portal access control)
- [ ] Audit logging enabled on all decision endpoints
- [ ] Static export tested (Next.js `npm run build` outputs standalone)
- [ ] Offline functionality tested (dashboard works with cached data)
- [ ] Error boundaries in React (no white screens on API failures)
- [ ] PII/secrets scrubbed from logs (no API keys in audit logs)

### Production Launch Criteria

- [ ] **Accuracy:** Model backtested 73%+ win rate on historical IDX trades
- [ ] **Governance:** 100% of decisions have audit trail + approval signatures
- [ ] **Compliance:** Risk officer veto works, mandate breaches prevented pre-execution
- [ ] **Performance:** Dashboard < 2s load, API < 200ms latency (p95)
- [ ] **Reliability:** 99.9% uptime on decision workflow (< 1 failure per 1000 analyses)
- [ ] **Documentation:** README, API docs, agent role docs, decision framework
- [ ] **Ops Ready:** Scaling plan for 10+ stocks/day, monitoring/alerting setup

---

## PART 9: LONG-TERM VISION (Beyond MVP)

### Year 2: Multi-Strategy Support
- Add options strategy agents (covered calls, collars)
- Add momentum/reversion agents for shorter holding periods
- Multi-asset (stocks + bonds + commodities)

### Year 3: Real Execution
- Broker API integration (IDX brokers: CIMB Niaga, Mandiri Securities, etc.)
- Live order placement + fill tracking
- Trade execution risk management (slippage, partial fills, rejections)

### Year 4: Scalability
- 100+ investor logins, each with custom mandates
- Multi-fund setup (Growth fund, Dividend fund, Income fund)
- Platform licensing to other investment managers

---

## CONCLUSION

Karsa has **strong governance foundations**. What it needs now is **investment domain specialization**:

1. **Specialized agents** that understand fundamental, technical, sentiment, and risk analysis
2. **Three-layer knowledge** that allows agents to learn from past decisions
3. **CIO-friendly dashboard** showing entry/exit prices, conviction, win rates (not raw agent essays)
4. **Deterministic workflows** that convert debate into decisions into memos into trades
5. **IDX domain expertise** baked into every prompt (conglomerates, MSCI risks, dividend calendars)

The **reference projects** (TradingAgents, Investment-Team) provide proven patterns for multi-agent orchestration, RAG knowledge systems, and decision workflows. Karsa's **event-sourced architecture** and **strict governance model** give you the foundation to build an enterprise-grade system that a CIO can actually use.

**Next step:** Start with Phase 1 (Agent Architecture) in Sprint 51. Get `BBCA → BUY memo` working end-to-end in 2-3 weeks. Then iterate: knowledge system, dashboard, IDX context.

---

**Prepared by:** Claude (AI Engineer)  
**Repository:** https://github.com/skeithnight/karsa  
**References:** TradingAgents (84k ⭐), Investment-Team (Agno, 152 ⭐)