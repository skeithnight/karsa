# Karsa Repository Audit Report: Trading Desk Evaluation

**Date:** October 26, 2023  
**Auditor:** Lead Quantitative Trader / Systems Architect  
**Target:** `https://github.com/skeithnight/karsa`  
**Focus:** Viability for Live Trading Desk Integration, Signal Generation, and Risk Management  

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Architectural Audit: The Event-Sourced Reality](#2-architectural-audit-the-event-sourced-reality)
3. [Data Ingestion & Market Reality (Critical Gap)](#3-data-ingestion--market-reality-critical-gap)
4. [AI Orchestration & Signal Generation](#4-ai-orchestration--signal-generation)
5. [Execution, Risk, & Post-Trade Analysis](#5-execution-risk--post-trade-analysis)
6. [Frontend & User Experience (CIO Console)](#6-frontend--user-experience-cio-console)
7. [Strategic Recommendations & Path to Production](#7-strategic-recommendations--path-to-production)

---

## 1. Executive Summary

**Verdict: Tier-1 Governance Architecture, Currently Lacking Live Market Plumbing.**

Karsa is a highly sophisticated, enterprise-grade AI orchestration and governance framework. It successfully solves the "black box" problem of autonomous AI by providing immutable audit trails, thesis ranking, and executive oversight. 

However, **in its current state, it is not a standalone trading system.** It is a "Bring Your Own Data" (BYOD) and "Bring Your Own Execution" (BYOE) platform. The codebase contains zero functional integrations for real-time market data, news feeds, or Direct Market Access (DMA). 

To use Karsa on a live desk, the engineering team must build external "Data Ingestion Workers" and an "Execution Bridge" to feed the system and act upon its signals.

---

## 2. Architectural Audit: The Event-Sourced Reality

Karsa is built on an **Event-Sourced / CQRS (Command Query Responsibility Segregation)** architecture. This is excellent for auditability but creates a specific operational reality for the trading desk.

### 2.1 The "Passive Ledger" Design
Karsa does not actively poll the outside world. It is designed to be a passive ledger that reacts to events pushed into its database. 
*   **Strength:** This prevents rate-limiting, handles massive scale, and ensures a perfect, immutable chronological history of every market state and AI decision.
*   **Weakness:** It makes the system entirely dependent on external actors to push data into it.

### 2.2 The "Empty Shell" Abstractions
An audit of the `src/` directory reveals that the foundational interfaces for external data are built, but the concrete implementations are missing.
*   **File:** `src/karsa/providers/domain/client.py`
*   **Finding:** Contains the abstract `ProviderClient` with methods like `fetch_asset()` and `fetch_universe()`. 
*   **Reality:** There are **zero** concrete implementations (e.g., no `PolygonProvider`, no `BloombergProvider`, no `YFinanceProvider`) anywhere in the codebase. The plumbing is laid, but the pipes are not connected to any water source.

---

## 3. Data Ingestion & Market Reality (Critical Gap)

This is the most critical finding for a live trading desk. **Karsa is currently blind to the real world.**

### 3.1 Lack of Market Data & Pricing APIs
*   There are no WebSocket or REST clients configured to fetch Level 1/Level 2 order book data, tick data, or end-of-day pricing.
*   Without real price feeds, the AI agents cannot calculate technical indicators, evaluate current valuation, or trigger price-based entry/exit signals.

### 3.2 Lack of News & Alternative Data
*   While architectural docs (`docs/architecture/59-idx-research-platform.md`) mention planned integrations with Yahoo Finance, Exa (web search), and StockTwits, **none of this code exists in `src/`**.
*   **File:** `src/karsa/research/api.py`
*   **Finding:** The research endpoint is a literal stub:
    ```python
    @router.get("/reports")
    def list_research_reports(...) -> Dict[str, Any]:
        """List research reports. Stub: returns empty."""
        return {"data": [], "next_cursor": None}
    ```

### 3.3 Trader Impact
If deployed today, the AI agents will generate theses based on static, hardcoded, or manually injected test data. **Alpha generation is currently impossible without a custom-built external data bridge.**

---

## 4. AI Orchestration & Signal Generation

Assuming the data gap is fixed, Karsa’s core value proposition lies in how it manages AI outputs.

### 4.1 The Thesis Hub (Signal Funnel)
*   **Function:** Aggregates AI-generated investment theses and ranks them by conviction and risk.
*   **Trader Value:** Solves the "AI noise" problem. Instead of reviewing 100 raw LLM outputs, the trader uses the Thesis Hub to filter for the top 5 high-conviction, uncorrelated signals.

### 4.2 Immutable Decision Ledgers (Auditability)
*   **Function:** Logs the AI's exact intent, expected time horizon, and confidence intervals *prior* to execution.
*   **Trader Value:** Crucial for debugging alpha decay. If a trade fails, the trader can read the ledger to determine if the AI's fundamental thesis was wrong, or if the market regime simply shifted. This prevents the "why did the AI do that?" black-box frustration.

### 4.3 LLM Integration
*   The codebase includes references to Google Gemini API keys, indicating the LLM layer is functional. However, without a Retrieval-Augmented Generation (RAG) pipeline connected to live news/data (see Section 3), the LLM is operating in a vacuum.

---

## 5. Execution, Risk, & Post-Trade Analysis

### 5.1 Direct Market Access (DMA) & Execution
*   **Finding:** There is no FIX engine integration, no broker API connectors (Interactive Brokers, Alpaca, etc.), and no Execution Management System (EMS) routing.
*   **Trader Impact:** Karsa will tell you *what* to buy and *how much*, but it will not click the button. You must build an API listener that reads Karsa's "Capital Deployment" events and routes them to your actual execution venue.

### 5.2 Risk Management & Sizing
*   **Finding:** The architecture includes modules for "volatility scaling" and "ex-post performance return decomposition."
*   **Reality Check:** These mathematical models require live historical and real-time variance/covariance data to function. Until the market data gap is filled, these risk modules are purely theoretical UI elements.

### 5.3 Post-Mortem & Governance
*   **Strength:** The "Failure Regime Tracking" and "Qualitative Session Management" are excellent for PMs reviewing desk performance at the end of the week. It shifts post-trade analysis from purely quantitative PnL to qualitative AI-behavior review.

---

## 6. Frontend & User Experience (CIO Console)

The `karsa-web/` directory contains a Next.js-powered frontend.

*   **CIO Dashboard:** Provides a top-down executive view. Excellent for Portfolio Managers who need to see capital allocation and daily pipeline shifts at a glance.
*   **AG Grid Integration:** The use of AG Grid for the Thesis Hub and Intelligence Timeline indicates a focus on high-density, professional-grade data visualization. It feels like a Bloomberg terminal workspace rather than a consumer web app.
*   **Verdict:** The UI is highly aligned with institutional trader workflows. It prioritizes data density and rapid filtering over flashy animations.

---

## 7. Strategic Recommendations & Path to Production

To transition Karsa from a "governance prototype" to a "live trading desk tool," the following engineering sprints are mandatory:

### Phase 1: The Data Bridge (Critical Priority)
*   **Action:** Build external Python workers using `polygon-io`, `alpaca-trade-api`, or `yfinance`.
*   **Task:** These workers must fetch real-time/daily pricing and news, format them into Karsa's expected event schema, and push them into the Karsa PostgreSQL/TimescaleDB event stream.
*   **Goal:** Give the AI "eyes and ears."

### Phase 2: The "Brain" Upgrade - LLM Pooling, RAG, & Governance (Critical Priority)

To make the AI agents viable for live capital allocation, the LLM layer must be upgraded from simple text generation to a resilient, memory-augmented reasoning engine.

#### 2.1 Implement LLM Pool & Smart Routing
*   **Action:** Integrate **LiteLLM** or **Portkey** into the Karsa backend.
*   **Task:** Configure a multi-provider pool (OpenAI, Anthropic, Mistral, local Llama). Implement semantic routing so complex thesis generation uses frontier models, while data-parsing tasks use cheaper/faster models. Implement automatic failover for rate limits and outages.
*   **Goal:** 99.99% uptime for signal generation and optimized API spend.

#### 2.2 Institutional Memory via RAG (Retrieval-Augmented Generation)
*   **Action:** Deploy a Vector Database (e.g., `pgvector` or Qdrant) alongside the existing PostgreSQL event store.
*   **Task:** Create an ingestion pipeline that embeds all "Immutable Decision Ledgers," post-mortems, and invalidated theses. Update the AI agent prompts to query this vector DB *before* generating a new signal.
*   **Goal:** Prevent the AI from repeating historical mistakes and allow it to build on past successful theses (Institutional Memory).

#### 2.3 LLM-as-a-Judge Governance Layer
*   **Action:** Implement a secondary "Risk Officer" LLM pipeline.
*   **Task:** Before any "Capital Deployment" event is finalized, route the proposed thesis through a strict, low-temperature LLM prompt designed to check for:
    1. Hallucinations (cross-referencing claims against the News RAG database).
    2. Risk limit breaches (checking proposed size against desk VaR).
    3. Logical consistency (ensuring the stop-loss aligns with the stated thesis horizon).
*   **Goal:** Zero "black box" execution. Every trade must pass an automated, AI-driven compliance check.

### Phase 3: The Execution Bridge
*   **Action:** Build a FastAPI or gRPC microservice that subscribes to Karsa's "Approved Thesis / Capital Deployment" events.
*   **Task:** This service will translate Karsa's signals into FIX messages or broker-specific API calls (e.g., IBKR TWS API) to execute the trades.

### Phase 4: Live Risk Calibration
*   **Action:** Once real price data is flowing, calibrate the "volatility scaling" algorithms using actual historical tick data to ensure position sizing aligns with the desk's Value at Risk (VaR) limits.

---

## Final Sign-Off

**Architecture:** 9/10 (Excellent event-sourced design, highly auditable).  
**Current Completeness for Live Trading:** 3/10 (Missing all external data and execution integrations).  
**Recommendation:** **Adopt as the "Brain", but build your own "Muscle and Senses".** Do not deploy to production until Phase 1 and Phase 3 of the roadmap are completed.