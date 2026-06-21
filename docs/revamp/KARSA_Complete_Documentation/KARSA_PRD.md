# KARSA Investment Firm Agent - Product Requirements Document (PRD)

**Version:** 1.0  
**Last Updated:** June 2026  
**Status:** Ready for Development  
**Product Manager:** Investment Platform Team  
**Target Release:** Q3 2026 (Sprint 51-56, 12 weeks)

---

## 1. EXECUTIVE SUMMARY

### 1.1 Product Vision

**Karsa CIO Dashboard** transforms autonomous AI investment agents into an enterprise-grade investment firm operating system.

### 1.2 Problem Statement

Investment firms deploying AI agents face a "black box" problem with no governance/audit trails, no CIO visibility, and no performance feedback loops.

### 1.3 Solution

Build a specialized dashboard that enforces mandate compliance, synthesizes agent debates into executive decisions, tracks realized returns, and provides continuous improvement through feedback loops.

### 1.4 Success Metrics

| Metric | Target |
|--------|--------|
| Decision Accuracy | 73%+ |
| Governance Coverage | 100% |
| Mandate Compliance | 100% |
| Dashboard Adoption | 95%+ |
| Latency (Analysis) | < 5 min |
| Latency (Dashboard) | < 2 sec |
| System Uptime | 99.9% |

---

## 2. PRODUCT OVERVIEW

### 2.1 Core Features (MVP Phase 1-3)

#### Feature 1: Investment Decision Pipeline
- Parallel agent analysis (Fundamentals, Technical, Sentiment, Risk, Macro)
- Researcher debate (Bull vs Bear synthesis)
- Portfolio Manager synthesis
- Risk Officer veto
- Committee Chair final review
- Structured memo output
- Audit logging

#### Feature 2: CIO Executive Dashboard
- Tier 1: Executive summary (portfolio, risk, today's decisions)
- Tier 2: Detailed analysis (holdings, risk, attribution)
- Tier 3: Full drill-down (memos, history, audit)
- Static export (offline capable)
- Mobile-responsive

#### Feature 3: Investment Memo Management
- Structured document format
- Approval workflow (PM → Risk → Chair)
- Version history
- Realized return tracking
- Comparison (target vs actual)

#### Feature 4: Three-Layer Knowledge System
- Layer 1: Static context (mandate, policy, IDX knowledge)
- Layer 2: Research library (RAG, PgVector)
- Layer 3: Memo archive (past decisions + realized returns)

#### Feature 5: Risk & Compliance Engine
- Automated mandate checking
- Real-time compliance verification
- Veto workflow
- Escalation system

#### Feature 6: Performance Attribution & Backtesting
- Daily P&L snapshots
- Attribution breakdown (selection, allocation, beta, residual)
- Win rate analysis
- Backtest framework

---

## 3. USER PERSONAS

### 3.1 Chief Investment Officer (CIO)
- Goals: Approve decisions, monitor risk, report to Board
- Needs: 5-second summary, mandate guarantees, realized return tracking
- Frequency: Daily (5-10 min) + deep dive 2x/week
- Dashboard: Executive summary + holdings table + risk heatmap

### 3.2 Portfolio Manager (PM)
- Goals: Generate alpha, size positions, write memos
- Needs: Agent analysis → synthesis, mandate checker, version history
- Frequency: Continuous (market hours)
- Tools: Analyst outputs, memo editor, mandate checker

### 3.3 Risk Officer
- Goals: Prevent mandate violations, manage risk
- Needs: Automated mandate checker, risk heatmap, escalation
- Frequency: Per decision (<1 min)
- Dashboard: Risk traffic light, sector allocation, correlation

### 3.4 AI Agent
- Goals: Generate accurate recommendations with conviction
- Needs: Knowledge layer, realized return feedback, context injection
- Frequency: Per-stock analysis
- Integration: Prompts + knowledge retrieval + memo writing

---

## 4. ACCEPTANCE CRITERIA

### Decision Pipeline
- ✅ Agent analysis runs parallel in <3 min
- ✅ Debate completes in <2 min
- ✅ PM synthesis in <2 min
- ✅ Risk veto in <30 sec
- ✅ Committee review in <1 min
- ✅ Total time <10 min

### Dashboard
- ✅ Load time <2 seconds
- ✅ Portfolio NAV + returns displayed
- ✅ Risk traffic light shows 6 metrics
- ✅ Today's decisions visible (3-5 cards)
- ✅ Clicking holding opens full memo
- ✅ Mobile responsive

### Risk Compliance
- ✅ 100% of positions pass mandate checks
- ✅ Zero sector violations
- ✅ Zero concentration violations
- ✅ Risk officer can veto in <1 min

---

## 5. TIMELINE & ROADMAP

| Phase | Duration | Features | Milestone |
|-------|----------|----------|-----------|
| P1 | Weeks 1-3 | Agent architecture, investment workflow | MVP: BBCA → approved memo |
| P2 | Weeks 4-5 | Knowledge system, RAG, memo archive | Agents learn from past decisions |
| P3 | Weeks 6-8 | CIO dashboard, UI components | Dashboard launch, CIO adoption |
| P4 | Weeks 9-10 | Governance, audit, performance attribution | Full governance + compliance |
| P5 | Weeks 11-12 | IDX domain, backtesting, refinement | Production-ready |

**Release Date: End of Q3 2026**

[... Full PRD continues with detailed sections ...]
