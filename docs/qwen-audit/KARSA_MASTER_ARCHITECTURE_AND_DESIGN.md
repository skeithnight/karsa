# Karsa System Audit & Architecture Design Report

**Date:** October 26, 2023  
**Auditor/Architect:** Lead Quantitative Trader / Systems Architect  
**Target:** `https://github.com/skeithnight/karsa`  
**Focus:** Viability for Live Trading Desk Integration, Signal Generation, Risk Management, and Production Architecture  

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Architectural Audit: The Event-Sourced Reality](#2-architectural-audit-the-event-sourced-reality)
3. [Data Ingestion & Market Reality (Critical Gap)](#3-data-ingestion--market-reality-critical-gap)
4. [AI Orchestration, LLM Pooling & Signal Generation](#4-ai-orchestration-llm-pooling--signal-generation)
5. [Execution, Risk, & Post-Trade Analysis](#5-execution-risk--post-trade-analysis)
6. [Frontend & User Experience (CIO Console)](#6-frontend--user-experience-cio-console)
7. [Proposed Event-Driven Architecture (The Upgrade)](#7-proposed-event-driven-architecture-the-upgrade)
8. [The Data Bridge: Technical Design Overview](#8-the-data-bridge-technical-design-overview)
9. [Strategic Recommendations & Path to Production](#9-strategic-recommendations--path-to-production)

---

## 1. Executive Summary

**Verdict: Tier-1 Governance Architecture, Currently Lacking Live Market Plumbing.**

Karsa is a highly sophisticated, enterprise-grade AI orchestration and governance framework. It successfully solves the "black box" problem of autonomous AI by providing immutable audit trails, thesis ranking, and executive oversight. 

However, **in its current state, it is not a standalone trading system.** It is a "Bring Your Own Data" (BYOD) and "Bring Your Own Execution" (BYOE) platform. The codebase contains zero functional integrations for real-time market data, news feeds, or Direct Market Access (DMA). 

To use Karsa on a live desk, the engineering team must build external "Data Ingestion Workers" and an "Execution Bridge" to feed the system and act upon its signals. This document outlines the exact architecture required to bridge this gap.

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
*   **Reality:** There are **zero** concrete implementations (e.g., no `PolygonProvider`, no `BloombergProvider`) anywhere in the codebase. The plumbing is laid, but the pipes are not connected to any water source.

---

## 3. Data Ingestion & Market Reality (Critical Gap)

This is the most critical finding for a live trading desk. **Karsa is currently blind to the real world.**

### 3.1 Lack of Market Data & Pricing APIs
*   There are no WebSocket or REST clients configured to fetch Level 1/Level 2 order book data, tick data, or end-of-day pricing.
*   Without real price feeds, the AI agents cannot calculate technical indicators, evaluate current valuation, or trigger price-based entry/exit signals.

### 3.2 Lack of News & Alternative Data
*   While architectural docs mention planned integrations with Yahoo Finance, Exa, and StockTwits, **none of this code exists in `src/`**.
*   **File:** `src/karsa/research/api.py`
*   **Finding:** The research endpoint is a literal stub returning empty arrays.

### 3.3 Trader Impact
If deployed today, the AI agents will generate theses based on static, hardcoded, or manually injected test data. **Alpha generation is currently impossible without a custom-built external data bridge.**

---

## 4. AI Orchestration, LLM Pooling & Signal Generation

Assuming the data gap is fixed, Karsa’s core value proposition lies in how it manages AI outputs. To make this production-ready, we must upgrade the LLM layer.

### 4.1 The Thesis Hub (Signal Funnel)
*   **Function:** Aggregates AI-generated investment theses and ranks them by conviction and risk.
*   **Trader Value:** Solves the "AI noise" problem. The trader uses the Thesis Hub to filter for the top 5 high-conviction, uncorrelated signals.

### 4.2 Immutable Decision Ledgers (Auditability)
*   **Function:** Logs the AI's exact intent, expected time horizon, and confidence intervals *prior* to execution.
*   **Trader Value:** Crucial for debugging alpha decay. If a trade fails, the trader can read the ledger to determine if the AI's fundamental thesis was wrong, or if the market regime simply shifted.

### 4.3 LLM Pooling & Smart Routing (Proposed Upgrade)
*   **Current State:** Hardcoded references to a single LLM provider.
*   **Proposed Upgrade:** Implement an LLM Proxy (e.g., LiteLLM) to manage a pool of API keys (OpenAI, Anthropic, Mistral). 
*   **Benefit:** Provides automatic failover if a provider hits rate limits, and allows semantic routing (e.g., using GPT-4o for complex thesis generation, but GPT-4o-mini for simple news extraction) to optimize API costs.

### 4.4 Institutional Memory via RAG (Proposed Upgrade)
*   **Current State:** Stateless LLM calls.
*   **Proposed Upgrade:** Connect the Immutable Decision Ledgers to a Vector Database (RAG). Before generating a new thesis, the AI queries its past successes and failures, preventing it from repeating historical mistakes.

---

## 5. Execution, Risk, & Post-Trade Analysis

### 5.1 Direct Market Access (DMA) & Execution
*   **Finding:** There is no FIX engine integration, no broker API connectors, and no EMS routing.
*   **Trader Impact:** Karsa will tell you *what* to buy, but it will not click the button. You must build an Execution Bridge to route signals to your broker.

### 5.2 Risk Management & Sizing
*   **Finding:** The architecture includes modules for "volatility scaling" and "ex-post performance return decomposition."
*   **Reality Check:** These mathematical models require live historical and real-time variance/covariance data to function. Until the market data gap is filled, these risk modules are purely theoretical.

### 5.3 Post-Mortem & Governance
*   **Strength:** The "Failure Regime Tracking" and "Qualitative Session Management" are excellent for PMs reviewing desk performance. It shifts post-trade analysis from purely quantitative PnL to qualitative AI-behavior review.

---

## 6. Frontend & User Experience (CIO Console)

The `karsa-web/` directory contains a Next.js-powered frontend.

*   **CIO Dashboard:** Provides a top-down executive view. Excellent for Portfolio Managers who need to see capital allocation and daily pipeline shifts at a glance.
*   **AG Grid Integration:** The use of AG Grid for the Thesis Hub and Intelligence Timeline indicates a focus on high-density, professional-grade data visualization. It feels like a Bloomberg terminal workspace rather than a consumer web app.

---

## 7. Proposed Event-Driven Architecture (The Upgrade)

To solve the critical gaps identified in Sections 3 and 5, we must implement a strict Event-Driven Architecture. This separates **Data Ingestion (The Eyes/Ears)** from **Data Reasoning (The Brain/AI)**.

### 7.1 The Complete Event-Driven Flow

```text
[EXTERNAL WORLD]
   │
   ▼
1. `karsa-data-ingestion-worker` (The Data Bridge)
   (Fetches live prices from Polygon, news from Bloomberg)
   │
   ▼ (Emits: MarketDataEvent, NewsEvent)
[EVENT STORE / MESSAGE BROKER] (e.g., Kafka / Redis Streams / Postgres)
   │
   ├──────────────────────────────────────────────────────────┐
   ▼                                                          ▼
2. The "Researcher" AI Agent                             3. `karsa-projection-worker`
   (Consumes data, uses LLM Pool & RAG Memory)               (Updates UI Read-Models)
   │                                                          │
   ▼ (Emits: ThesisGeneratedEvent)                            ▼
[EVENT STORE]                                              [Next.js Frontend]
   │                                                        (Thesis Hub, Grids)
   ▼                                                          ▲
4. "LLM-as-a-Judge" Governance Agent                         │
   (Checks thesis against Risk Limits & Hallucinations)      │
   │                                                          │
   ▼ (Emits: ThesisApprovedEvent)                             │
[EVENT STORE] ───────────────────────────────────────────────┘
   │
   ├──────────────────────────────────────┐
   ▼                                      ▼
5. `karsa-cio-producer`                6. Execution Bridge (To Be Built)
   (Aggregates for CIO Dashboard)         (Routes to FIX/IBKR for actual trading)
   │                                      │
   ▼                                      ▼
[CIO Dashboard UI]                     [Broker / Exchange]
```

### 7.2 Worker Responsibilities

| Worker | Role | Why it Matters |
|--------|------|----------------|
| **`karsa-data-ingestion-worker`** | Fetches external data, normalizes it, and pushes it to the Event Store. | If the LLM goes down, market data keeps flowing. |
| **`karsa-projection-worker`** | Listens to raw events and updates the relational DB (Read-Models) for the UI. | Allows the Next.js AG Grid to filter/sort thousands of theses instantly without querying the raw event log. |
| **`karsa-cio-producer`** | Aggregates granular events into portfolio-level metrics (e.g., sector exposure, daily pipeline shifts). | Feeds the CIO Dashboard so the PM sees the "forest" (macro risk) instead of the "trees" (individual trades). |

---

## 8. The Data Bridge: Technical Design Overview

The `karsa-data-ingestion-worker` is the most critical new component. It is designed to be highly resilient, database-driven, and capable of zero-downtime updates.

### 8.1 Core Design Principles
1.  **Database-Driven Configuration:** Providers, API keys, and configs are stored in PostgreSQL. Adding a vendor requires zero code deployments.
2.  **Strict Normalization:** Downstream consumers never see vendor-specific payloads. Everything is translated to Karsa's unified Pydantic schema.
3.  **Token Optimization:** Raw tick data is aggregated into OHLCV bars before reaching the LLM to prevent burning through API token budgets.
4.  **Zero-Downtime Hot-Reloading:** Uses PostgreSQL `LISTEN/NOTIFY` to detect API key rotations or config changes, swapping connectors without restarting the worker.

### 8.2 Detailed Specifications
For the deep-dive technical implementations, database schemas, and code patterns for the Data Bridge, refer to the dedicated phase documents:
- **[Phase 1: Database Schema & Security](./Phase_1_Database_Schema.md)** (AES-256 encryption, Provider tables)
- **[Phase 2: Connectors & Normalization](./Phase_2_Connectors_and_Normalization.md)** (Factory pattern, Pydantic models)
- **[Phase 3: Aggregation & Event Emission](./Phase_3_Aggregation_and_Emission.md)** (Ticks to OHLCV bars, Kafka/Redis emission)
- **[Phase 4: Operations, Hot-Reload & Health](./Phase_4_Operations_and_HotReload.md)** (Blue/Green swaps, Failover logic)

---

## 9. Strategic Recommendations & Path to Production

To transition Karsa from a "governance prototype" to a "live trading desk tool," the following engineering sprints are mandatory:

### Phase 1: The Data Bridge (Critical Priority)
*   **Action:** Build the `karsa-data-ingestion-worker` using the DB-driven design.
*   **Task:** Implement the Connector Factory, integrate Polygon (Equities) and Finnhub (News), and build the Normalization/Aggregation engines.
*   **Goal:** Give the AI "eyes and ears" with standardized, LLM-friendly OHLCV bars and filtered news.

### Phase 2: Grounding the AI (RAG & LLM Pool)
*   **Action:** Integrate LiteLLM for multi-provider routing and deploy a Vector DB (e.g., pgvector).
*   **Task:** Embed past Immutable Decision Ledgers into the Vector DB. Update AI agent prompts to query this memory and pass through an "LLM-as-a-Judge" governance check before emitting a `ThesisApprovedEvent`.
*   **Goal:** Prevent hallucinations, optimize API costs, and build institutional memory.

### Phase 3: The Execution Bridge
*   **Action:** Build a FastAPI microservice that subscribes to `ThesisApprovedEvent`.
*   **Task:** Translate Karsa's signals into broker-specific API calls (e.g., IBKR TWS API or Alpaca) to execute the trades. Implement basic slippage and market-impact checks.
*   **Goal:** Close the loop from signal generation to actual market execution.

### Phase 4: Live Risk Calibration & CIO Dashboards
*   **Action:** Calibrate the "volatility scaling" algorithms using actual historical tick data.
*   **Task:** Ensure the `karsa-cio-producer` is accurately aggregating sector exposures and feeding the CIO Dashboard in real-time.
*   **Goal:** Ensure position sizing aligns with the desk's Value at Risk (VaR) limits and provides true executive oversight.

---

## Final Sign-Off

**Architecture:** 9/10 (Excellent event-sourced design, highly auditable).  
**Current Completeness for Live Trading:** 3/10 (Missing all external data and execution integrations).  
**Recommendation:** **Adopt as the "Brain", but build your own "Muscle and Senses".** Do not deploy to production until Phase 1 (Data Bridge) and Phase 3 (Execution Bridge) of the roadmap are completed.
```