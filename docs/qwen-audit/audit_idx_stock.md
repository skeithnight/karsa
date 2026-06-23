# Karsa IDX Trading System: Strategic Audit & Implementation Roadmap

**Date:** June 23, 2026  
**Target:** `https://github.com/skeithnight/karsa`  
**Focus:** Transitioning Karsa from an architectural prototype to a live, signal-generating system for the Indonesia Stock Exchange (IDX).

---

## 1. Executive Summary

**Verdict: The "Brain" is Institutional-Grade; the "Nervous System" is Disconnected.**

A comprehensive audit of the Karsa repository reveals a massive leap in development. The core domain models, risk policies, and IDX-specific mandates are production-quality. The system successfully implements sophisticated multi-phase workflows, deterministic risk engines, and immutable audit trails. 

However, the system is currently operating in a vacuum. The "plumbing" layer—live market data ingestion and actual broker execution—is missing. Furthermore, the original architectural designs (Sprints 51-59) assumed a US-centric infrastructure (Polygon, Finnhub, Alpaca, IBKR), which is incompatible with the realities of the Indonesia Stock Exchange (IDX).

This document outlines the critical gaps, highlights the "hidden alpha" already built into the codebase, and provides a concrete, step-by-step action plan to pivot the architecture for IDX and generate live signals immediately.

---

## 2. Current State Audit: What's Working & Institutional-Grade

The existing codebase contains several features that rival institutional quantitative platforms. These are the core strengths that must be preserved and leveraged.

### 2.1 The Investment Decision Pipeline
The multi-phase workflow is fully designed and partially implemented with high precision:
*   **`SignificanceFilter` (Cost Gate):** A brilliant implementation that only triggers LLM calls when a price moves >2%, correlated news arrives, or a scheduled rebalance window opens. This is exactly the right pattern for IDX's volatility profile, preventing LLM cost bankruptcy.
*   **`TradeThesis` Aggregate:** Clean event-sourced Domain-Driven Design (DDD) covering BUY/SELL/HOLD, time horizons (INTRADAY to LONG_TERM), conviction scores (0–1), and strict stop-loss/take-profit parameters.
*   **`ConvictionScore` Value Object:** Correctly maps analyst agreement (e.g., STRONG = 3–4 agents agree with ≥6.0/10 each).

### 2.2 The Hard Risk Engine
The `HardRiskEngine` is purely deterministic and non-AI. It enforces hard survival limits:
*   $500K max single order (or equivalent IDR limit).
*   5% max position size.
*   $5M daily turnover circuit breaker.

### 2.3 IDX-Specific Mandate (`MANDATE.md`)
This is where Karsa separates itself from retail platforms. The mandate is genuinely tailored for the Indonesian market:
*   **Universe Constraints:** IDX-listed only, market cap >IDR 5T, daily volume >IDR 1B.
*   **Conglomerate Exposure Tracking:** Explicitly tracks cross-holdings between Prajogo (TPIA, BREN, CUAN), Sinar Mas (SMGR, INDF), Astra, and Bakrie groups. Standard tools treat these as separate stocks; Karsa correctly treats them as single correlated exposure units.
*   **MSCI Float Monitoring:** Flags stocks at risk if free-float <18% and triggers rebalances on MSCI reclassification events.
*   **Macro Circuit Breakers:** Hardcoded triggers for Rupiah weakness (e.g., >5% weekly drop → reduce all positions 20%).

### 2.4 Attribution & Calibration
*   **Brinson Attribution Model:** `AttributionBreakdown` decomposes returns into Selection + Allocation + Beta + Residual.
*   **Brier Score Calibration:** Grades conviction scores against realized outcomes. If "STRONG" calls win <60%, the system flags recalibration. This is institutional-grade feedback.

---

## 3. Critical Gaps for Live IDX Trading

While the domain logic is flawless, the system cannot trade in the real world yet. 

### 3.1 Data Bridge (Sprints 51–53)
*   **The Gap:** There is no live IDX data ingestion. The `providers` module is architected, but actual connectors are missing. 
*   **The IDX Reality:** US providers like Polygon and Finnhub have weak or non-existent intraday coverage for IDX. `DECISION_PROCESS.md` assumes YFinance, which works for End-of-Day (EOD) but not intraday.

### 3.2 AI Grounding (Sprints 54–55)
*   **The Gap:** The `ResearcherAgent` class exists, but the RAG infrastructure (pgvector, embedding pipeline) isn't fully wired. The `GovernanceAgent` is scaffolded but not connected to a live LLM pool.
*   **Sentiment Data:** Indonesian sentiment data is sparse by design. The system correctly rates the Sentiment Analyst at 5/10 confidence, but StockBit API is mentioned and not connected.

### 3.3 Broker Execution (Sprints 56–57)
*   **The Gap:** The `HardRiskEngine` is implemented, but the broker adapters are designed for US markets.
*   **The IDX Reality:** **Neither Alpaca nor Interactive Brokers (IBKR) connects to the IDX directly.** To trade live, you need a local broker bridge (Mandiri Sekuritas, BRI Danareksa, Indo Premier, or RHB), which none of the current code addresses.

---

## 4. The IDX Pivot: Adapting the Architecture

To make Karsa work for the Indonesia Stock Exchange, we must pivot the implementation of the Data and Execution bridges away from US-centric tools.

### 4.1 The Data Bridge Pivot
*   **Original Design:** Polygon (WebSocket) + Finnhub (REST).
*   **IDX Pivot:** Use **YFinance** for End-of-Day (EOD) data as the MVP. YFinance provides reliable daily OHLCV for IDX tickers (e.g., `BBCA.JK`). The `SignificanceFilter` will work perfectly with EOD data to trigger thesis generation only on major daily moves. *Intraday data can be added later via local APIs like RTI Business if strictly required.*

### 4.2 The Execution Bridge Pivot
*   **Original Design:** Alpaca / IBKR Adapters.
*   **IDX Pivot:** Build an **IDX Paper-Trading Mock Adapter**. Instead of sending FIX messages to an exchange, this adapter will simulate fills based on the next day's opening price (for EOD signals) or VWAP, and log the result directly into the **Immutable Decision Journal**. This validates the entire lifecycle without risking capital or requiring complex local broker API integrations.

---

## 5. "Bridge the Gap" Action Plan

To get live IDX signals flowing immediately without getting bogged down in building live broker APIs, follow this exact 4-step sequence:

### Step 1: Wire YFinance to the Significance Filter (Day 1)
1.  Write a Python script that pulls EOD data for the core IDX universe (e.g., BBCA, BBRI, TLKM, ASII, ANTM) using `yfinance`.
2.  Feed this data into the existing `SignificanceFilter`.
3.  **Goal:** Prove that the filter correctly ignores flat days and only triggers the LLM when a stock moves >2% or hits a volume spike.

### Step 2: Build the IDX Paper-Trading Mock (Day 2)
1.  Create an `IDXMockBrokerAdapter` that implements the `BrokerAdapterPort`.
2.  When the `HardRiskEngine` approves a `ThesisApprovedEvent`, this mock adapter calculates the theoretical fill price (e.g., next day's open) and logs the trade to the `DecisionJournal`.
3.  **Goal:** Validate the entire lifecycle (Signal → Risk Check → Execution → Journal) without risking a single Rupiah.

### Step 3: Activate the AI Brain (Day 3)
1.  Connect the `ResearcherAgent` and `GovernanceAgent` to the YFinance data stream.
2.  Ensure the `GovernanceAgent` (LLM-as-a-Judge) is actively rejecting hallucinations (e.g., if the AI claims a local Indonesian company did something it didn't).
3.  **Goal:** Generate your first batch of live, governance-approved IDX trade theses.

### Step 4: Build the IDX Research Terminal (Day 4-5)
1.  Use the existing Next.js `karsa-web` architecture to build the frontend.
2.  Focus on the **Thesis Hub** (AG Grid) and the **Decision Journal** (Timeline).
3.  Implement the **Conglomerate Exposure Heatmap** to visually track Prajogo/Sinar Mas/Astra risks.
4.  **Goal:** Give yourself a visual dashboard to read the AI's reasoning and review the Brier score calibration.

---

## 6. Final Verdict & Next Steps

The Karsa repository is further along than it might look from the outside. The domain model, risk policy, and mandate are production-quality for IDX investing. 

**Your immediate priority is not to build complex live broker integrations.** Your priority is to **fake the data and execution** just enough to get the AI agents generating and validating live IDX signals. 

Once you trust the AI's output in the Decision Journal and see the Brier scores validating the conviction models, *then* you can spend the engineering effort to build a live API bridge to a local broker like Mandiri Sekuritas or Indo Premier.

### Immediate Next Actions for Engineering:
1.  **Merge/Review:** Ensure all Sprint 51-59 unit tests (committed in `59eeafa`) are passing in CI/CD.
2.  **Implement Step 1:** Write the YFinance ingestion script today.
3.  **Implement Step 2:** Write the `IDXMockBrokerAdapter` tomorrow.
4.  **Audit:** Use the previously generated audit prompts to ensure the `SignificanceFilter` and `HardRiskEngine` are strictly enforced in the new code.