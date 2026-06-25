# Consolidated Roadmap & Dashboard

## Current Architecture Baseline
- Status: IMPLEMENTATION_COMPLETE (Sprint-44 Review & Post-Mortem Foundation Implemented)
- Core Capabilities: Scalable bounded contexts, event-driven deterministic execution, capability-based security, write-once immutable decision ledgers, portfolio-level orchestration, dual-signature PEP validations, pre-outcome reasoning ledger, hindsight-prevention controls, authoritative decision authorization layer, ex-ante parametric risk engine, concentration and liquidity analysis, regime-aware volatility scaling, stress scenario testing, compliance policy lifecycles, Ed25519 double-signature Exception override verification, cost attribution models, performance-outcome calibration curves, ex-post performance return decomposition (selection, allocation, execution, beta, and residual returns), deterministic recomputation chains, qualitative review sessions, append-only post-mortem consensus ledgers, quarterly range partitioning, immutable database-level triggers, deterministic consensus solving, and review invalidation and lineage tracking.

## Current ADR Count
- Total Active Architecture Decision Records: 70

## Current Sprint Status
- Sprint-01 Closed
- Sprint-02 Closed
- Sprint-03 Closed
- Sprint-04 Closed
- Sprint-05 Closed
- Sprint-06 Closed
- Sprint-07 Closed
- Sprint-08 Closed
- Sprint-09 Closed
- Sprint-10 Closed
- Sprint-11 Closed
- Sprint-11.5 Closed
- Sprint-12 Closed
- Sprint-13 Closed
- Sprint-14 Closed
- Sprint-15 Closed
- Sprint-16 Closed (Complete with Debt)
- Sprint-17 Closed (Complete with Debt)
- Sprint-18 Closed (Implementation Complete)
- Sprint-19 Closed (Implementation Complete)
- Sprint-20 Closed (Implementation Complete)
- Sprint-21 Closed (Architecture Design Only)
- Sprint-22 Closed (Implementation Complete)
- Sprint-23 Closed (Architecture Design Only)
- Sprint-24 Closed (Implementation Complete)
- Sprint-25 Closed (Implementation Complete)
- Sprint-26 Closed (Architecture Design Only)
- Sprint-27 Closed (Architecture Design Only)
- Sprint-28 Closed (Architecture Design Only)
- Sprint-29 Closed (Architecture Design Only)
- Sprint-30 Closed (Architecture Design Only)
- Sprint-31 Closed (Architecture Design Only)
- Sprint-32 Closed (Architecture Design Frozen & Gap Analysis Complete)
- Sprint-33 Closed (Implementation Complete & Audited)
- Sprint-34 Closed (Architecture Design Frozen)
- Sprint-35 Closed (IMPLEMENTATION_COMPLETE, AUDIT_COMPLETE, REMEDIATION_COMPLETE, FULLY_COMPLIANT)
- Sprint-37 Closed (IMPLEMENTATION_COMPLETE, AUDIT_COMPLETE, REMEDIATION_COMPLETE, FULLY_COMPLIANT)
- Sprint-38 Closed (IMPLEMENTATION_COMPLETE, AUDIT_COMPLETE, REMEDIATION_COMPLETE, FULLY_COMPLIANT)
- Sprint-39 Closed (IMPLEMENTATION_COMPLETE, AUDIT_COMPLETE, REMEDIATION_COMPLETE, FULLY_COMPLIANT)
- Sprint-40 Closed (IMPLEMENTATION_COMPLETE, AUDIT_COMPLETE, REMEDIATION_COMPLETE, FULLY_COMPLIANT)
- Sprint-41 Closed (IMPLEMENTATION_COMPLETE, AUDIT_COMPLETE, REMEDIATION_COMPLETE, FULLY_COMPLIANT)
- Sprint-42 Closed (SPRINT_42_CLOSED, FULLY_COMPLIANT, CLOSED_SPRINT_PROTECTED)
- Sprint-43 Closed (IMPLEMENTATION_COMPLETE, AUDIT_COMPLETE, FULLY_COMPLIANT, CLOSED_SPRINT_PROTECTED)
- Sprint-44 Closed (IMPLEMENTATION_COMPLETE, AUDIT_COMPLETE, REMEDIATION_COMPLETE, FULLY_COMPLIANT, CLOSED_SPRINT_PROTECTED)
- Sprint-45 Closed (IMPLEMENTATION_COMPLETE, AUDIT_COMPLETE, FULLY_COMPLIANT, CLOSED_SPRINT_PROTECTED)
- Sprint-46 Closed (IMPLEMENTATION_COMPLETE, AUDIT_COMPLETE, REMEDIATION_COMPLETE, FULLY_COMPLIANT, CLOSED_SPRINT_PROTECTED)
- Sprint-47 Closed (IMPLEMENTATION_COMPLETE, AUDIT_COMPLETE, REMEDIATION_COMPLETE, FULLY_COMPLIANT, CLOSED_SPRINT_PROTECTED)
- Sprint-48 Closed (IMPLEMENTATION_COMPLETE, AUDIT_COMPLETE, REMEDIATION_COMPLETE, FULLY_COMPLIANT, CLOSED_SPRINT_PROTECTED)
- Sprint-49 Closed (IMPLEMENTATION_COMPLETE, AUDIT_COMPLETE, REMEDIATION_COMPLETE, FULLY_COMPLIANT, CLOSED_SPRINT_PROTECTED)
- Sprint-50 Closed (IMPLEMENTATION_COMPLETE, AUDIT_COMPLETE, REMEDIATION_COMPLETE, PRODUCTION_READY, CLOSED_SPRINT_PROTECTED)

## Proposed Future Roadmap — Qwen Audit Remediation (Phases 1–4)
**Source:** `docs/qwen-audit/` — Architecture Audit & Engineering Specs
**Goal:** Transition Karsa from "governance prototype" to "live trading desk tool" by building the Data Bridge, AI Grounding, Execution Bridge, and CIO Dashboard.

### Phase 1: The Data Bridge (Critical Priority)
- **Sprint-51**: Data Bridge — Foundation & Schema (DB-driven provider management, AES-256 encryption, hot-reload via pg_notify, Connector Factory pattern)
- **Sprint-52**: Data Bridge — Connectors, Normalization & Aggregation (PolygonConnector, FinnhubConnector, Pydantic normalization, tick→OHLCV aggregation, event emission)
- **Sprint-53**: Data Bridge — Resilience, Health & Observability (Health Monitor, automatic provider failover, gap-filling, Slack alerts)

### Phase 2: Grounding the AI (Critical Priority, depends on Phase 1)
- **Sprint-54**: AI Grounding — LLM Pool & RAG Infrastructure (LiteLLM multi-provider routing, pgvector schema, embedding pipeline, context retrieval)
- **Sprint-55**: AI Grounding — Researcher & Governance Agents (ResearcherAgent thesis generation, GovernanceAgent LLM-as-a-Judge, Red Team test suite)

### Phase 3: The Execution Bridge (Critical Priority, depends on Phase 2)
- **Sprint-56**: Execution Bridge — Risk Engine & Order Management (Hard Pre-Trade Risk Engine, OMS state machine, TWAP slicer, kill switch, paper trading mode)
- **Sprint-57**: Execution Bridge — Broker Adapters & Feedback Loop (AlpacaAdapter, IBKRAdapter, WebSocket fill handling, execution event feedback loop)

### Phase 4: Live Risk & CIO Dashboards (Final Production Phase, depends on Phase 3)
- **Sprint-58**: Live Risk — Volatility Targeting & Position Sizing (EWMA volatility calculator, risk calibration engine, vol-targeted position sizing, audit trail)
- **Sprint-59**: CIO Dashboard — Producer, API & Real-Time Frontend (karsa-cio-producer, TimescaleDB read-models, REST+WebSocket API, Next.js CIO Dashboard, stale data circuit breaker)

### Phase 5: Frontend Console Revamp (Design Reference: `docs/revamp/karsa_console_revamp.html`)
- **Sprint-63**: Karsa Web Console Revamp — DESIGN phase complete. Restructure 12+ pages into 5-page model (Dashboard, Signals, Portfolio, Performance, Governance). Replace sidebar with top-tab navigation. Add ticker tape, conviction pips, conglomerate heatmap, Brier calibration. Unify all data fetching to React Query. Status: DESIGN