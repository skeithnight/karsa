# Gap Analysis

**Generated:** 2026-06-21
**Purpose:** Identify what doesn't exist and needs to be built
**Baseline:** Sprint-12 (Transport Layer complete)

---

## Current State Inventory

### Existing Bounded Contexts (20+)

| Module | Status | Capability |
|---|---|---|
| `allocation/` | Production | Capital allocation decisions |
| `attribution/` | Production | Attribution decomposition |
| `attribution_engine/` | Production | Multi-dimensional attribution |
| `capabilities/` | Production | Capability registration |
| `cio/` | Production | CIO decision pipeline |
| `decision_journal/` | Production | Decision logging |
| `evidence/` | Production | Evidence tracking |
| `execution/` | Production | Order lifecycle, broker port |
| `firm_intelligence/` | Production | Data mart projections |
| `governance/` | Production | Policy evaluation, exceptions |
| `governance_engine/` | Production | Trust scoring, governance actions |
| `market/` | Production | Market structure |
| `memory/` | Production | Platform memory |
| `performance/` | Production | Performance tracking |
| `performance_engine/` | Production | Performance projections |
| `portfolio/` | Production | Position management, NAV |
| `post_mortem/` | Production | Post-mortem analysis |
| `regime/` | Production | Regime detection |
| `review/` | Production | Review assessments |
| `review_engine/` | Production | Worker/thesis/capability reviews |
| `risk/` | Production | VaR, exposure management |
| `thesis/` | Production | Thesis lifecycle |
| `workflow/` | Production | Decision state machine |
| `capability_engine/` | Sprint-11 | Evolution, health, projections |
| `transport/` | Sprint-12 | FastAPI HTTP layer |

### Infrastructure

| Component | Status | Notes |
|---|---|---|
| PostgreSQL + Alembic | Production | Event store, projections |
| Docker Compose | Production | Multi-container orchestration |
| Next.js frontend | Production | Static export, shadcn/ui |
| Event sourcing | Production | Immutable domain events |
| CQRS | Production | Separate read/write models |
| Transactional outbox | Production | Reliable event publishing |
| OCC | Production | Optimistic concurrency on health scores |
| FastAPI transport | Sprint-12 | 11 endpoints, DI, exception mapper |

---

## Gap Identification

### Gap 1: Investment Workflow Domain

**What's Missing:**
- No analyst role abstractions (Fundamental, Technical, Sentiment, Risk, Market)
- No debate mechanism (Bull vs Bear)
- No investment-specific decision states (ANALYZING → DEBATING → DECIDING → APPROVED)
- No conviction scoring system

**What Exists:**
- `workflow/` module has generic decision state machine
- `governance/` has policy evaluation
- `cio/` has decision pipeline

**Action:** Create `investment_workflow/` bounded context

**Sprint:** 13

**Dependencies:** None (can start immediately)

---

### Gap 2: Investment Knowledge System

**What's Missing:**
- No research document storage with vector search
- No RAG-based retrieval for agent context
- No knowledge layering (static → research → memos)

**What Exists:**
- `memory/` module for platform memory
- PostgreSQL + pgvector available in Docker Compose

**Action:** Create `investment_knowledge/` bounded context

**Sprint:** 14

**Dependencies:** None

---

### Gap 3: Investment Memo Lifecycle

**What's Missing:**
- No structured investment memo format
- No memo approval workflow (PM → Risk → Chair)
- No realized return tracking (entry → exit → actual)
- No conviction calibration feedback loop

**What Exists:**
- `review_engine/` handles assessments (similar pattern)
- `decision_journal/` logs decisions (adjacent)

**Action:** Create `investment_memo/` bounded context

**Sprint:** 15

**Dependencies:** Gap 1 (workflow produces memos)

---

### Gap 4: CIO Dashboard Pages

**What's Missing:**
- No `/cio-dashboard/` route in karsa-web
- No portfolio status card component
- No risk traffic light component
- No stock decision card component
- No performance attribution chart

**What Exists:**
- `karsa-web/` has full component library (shadcn/ui, Recharts, AG Grid)
- `portfolio/` module has position data
- `risk/` module has risk data
- `attribution_engine/` has attribution data

**Action:** Extend `karsa-web/` with new pages and API endpoints

**Sprint:** 16-17

**Dependencies:** Gaps 1, 2, 3 (need data sources)

---

### Gap 5: Investment Mandate Rules

**What's Missing:**
- No sector allocation limit enforcement
- No concentration limit enforcement
- No conglomerate exposure tracking
- No mandate compliance checking per decision

**What Exists:**
- `governance/` has policy evaluation framework
- `governance_engine/` has trust scoring
- `risk/` has exposure management

**Action:** Extend `governance/` with investment-specific policies

**Sprint:** 18

**Dependencies:** Gap 1 (workflow triggers mandate checks)

---

### Gap 6: Investment Performance Attribution

**What's Missing:**
- No selection/allocation/beta/residual decomposition
- No conviction-correlated win rate analysis
- No backtest framework

**What Exists:**
- `attribution_engine/` has multi-dimensional attribution
- `performance_engine/` has performance projections

**Action:** Extend `attribution_engine/` with investment-specific dimensions

**Sprint:** 19

**Dependencies:** Gap 3 (realized returns feed attribution)

---

### Gap 7: IDX Domain Context

**What's Missing:**
- No IDX-specific agent prompts
- No conglomerate group mappings in code
- No MSCI float tracking
- No dividend calendar integration

**What Exists:**
- `docs/investment_context/` created in Phase 0 (DONE)

**Action:** Documentation + prompt injection templates

**Sprint:** 20

**Dependencies:** None (documentation only)

---

## Gap Priority Matrix

| Gap | Priority | Effort | Dependencies | Sprint |
|---|---|---|---|---|
| Gap 1: Investment Workflow | P0 | High | None | 13 |
| Gap 2: Knowledge System | P1 | Medium | None | 14 |
| Gap 3: Investment Memos | P1 | Medium | Gap 1 | 15 |
| Gap 4: CIO Dashboard | P1 | High | Gaps 1,2,3 | 16-17 |
| Gap 5: Mandate Rules | P2 | Medium | Gap 1 | 18 |
| Gap 6: Performance Attribution | P2 | Medium | Gap 3 | 19 |
| Gap 7: IDX Domain | P2 | Low | None | 20 |

---

## What Does NOT Need Building

The following revamp proposals already exist and should NOT be rebuilt:

| Proposal | Already Exists | Module |
|---|---|---|
| Event-sourced audit trail | ✓ | `shared/` + all bounded contexts |
| Risk management | ✓ | `risk/` |
| Portfolio management | ✓ | `portfolio/` |
| Execution engine | ✓ | `execution/` |
| Governance framework | ✓ | `governance/` |
| Review system | ✓ | `review_engine/` |
| Attribution system | ✓ | `attribution_engine/` |
| Decision journaling | ✓ | `decision_journal/` |
| Regime detection | ✓ | `regime/` |
| FastAPI transport | ✓ | `transport/` |
| Docker deployment | ✓ | `docker-compose.yml` |
| Next.js frontend | ✓ | `karsa-web/` |

---

## Phase 0 Completion Status

| Task | Status | Output |
|---|---|---|
| Extract IDX domain context | ✅ DONE | `docs/investment_context/MANDATE.md` |
| Extract risk policy rules | ✅ DONE | `docs/investment_context/RISK_POLICY.md` |
| Extract decision framework | ✅ DONE | `docs/investment_context/DECISION_PROCESS.md` |
| Map features to existing modules | ✅ DONE | `FEATURE_MAPPING.md` |
| Gap analysis | ✅ DONE | This document |
| CIO validates domain accuracy | ⏳ PENDING | Awaiting CIO review |
