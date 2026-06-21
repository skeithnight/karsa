# Feature-to-Module Mapping

**Generated:** 2026-06-21
**Purpose:** Map revamp proposals to existing bounded contexts
**Principle:** Extend existing. Build new only when no extension point exists.

---

## Mapping Matrix

### 1. Investment Decision Pipeline

| Revamp Proposal | Existing Module | Action | Notes |
|---|---|---|---|
| Analyst agents (Fundamental, Technical, Sentiment, Risk, Market) | None | **NEW** `investment_workflow/` | New bounded context with analyst role port interfaces |
| Bull/Bear debate | None | **NEW** `investment_workflow/` | Debate is part of workflow state machine |
| Portfolio Manager synthesis | `workflow/` | **EXTEND** | Add investment-specific decision states |
| Risk Officer veto | `governance/` | **EXTEND** | Add investment mandate rules |
| Committee Chair review | `governance/` | **EXTEND** | Add final approval workflow |
| Investment memo output | None | **NEW** `investment_memo/` | New bounded context for memo lifecycle |

### 2. CIO Dashboard

| Revamp Proposal | Existing Module | Action | Notes |
|---|---|---|---|
| Portfolio status card | `portfolio/` | **EXTEND** | Add NAV, Sharpe, drawdown endpoints |
| Risk traffic light | `risk/` | **EXTEND** | Add mandate comparison endpoints |
| Today's decisions | `investment_workflow/` | **NEW** | Queries from new workflow context |
| Holdings table | `portfolio/` | **EXTEND** | Existing position data |
| Stock decision cards | `investment_memo/` | **NEW** | Memo data + analyst scores |
| Risk heatmap | `risk/` | **EXTEND** | Sector allocation vs mandate |
| Performance attribution | `attribution_engine/` | **EXTEND** | Selection/allocation/beta/residual |
| Frontend pages | `karsa-web/` | **EXTEND** | New `/cio-dashboard/` routes |

### 3. Knowledge System

| Revamp Proposal | Existing Module | Action | Notes |
|---|---|---|---|
| Static context (mandate, policy) | None | **DOCS** | `docs/investment_context/` (done) |
| Research library (RAG) | `memory/` | **NEW** `investment_knowledge/` | New bounded context with PgVector |
| Memo archive | `investment_memo/` | **NEW** | Part of memo lifecycle |

### 4. Risk & Compliance

| Revamp Proposal | Existing Module | Action | Notes |
|---|---|---|---|
| Mandate checking | `governance/` | **EXTEND** | Add investment mandate rules |
| Sector limits | `governance/` | **EXTEND** | Add sector allocation policies |
| Concentration limits | `governance/` | **EXTEND** | Add concentration policies |
| Escalation system | `governance/` | **EXTEND** | Add severity-based escalation |
| Veto workflow | `governance_engine/` | **EXTEND** | Add investment veto states |

### 5. Performance Attribution

| Revamp Proposal | Existing Module | Action | Notes |
|---|---|---|---|
| P&L snapshots | `performance/` | **EXTEND** | Add daily NAV snapshots |
| Attribution breakdown | `attribution_engine/` | **EXTEND** | Add selection/allocation/beta/residual |
| Win rate analysis | `performance_engine/` | **EXTEND** | Add conviction-correlated win rates |
| Backtest framework | None | **NEW** `backtest/` | New bounded context (Phase 6) |
| Realized return tracking | `investment_memo/` | **NEW** | Close-loop feedback on memos |

### 6. IDX Domain

| Revamp Proposal | Existing Module | Action | Notes |
|---|---|---|---|
| Conglomerate groups | None | **DOCS** | `docs/investment_context/` (done) |
| MSCI float tracking | None | **DOCS** | Add to MANDATE.md |
| Dividend calendar | None | **DOCS** | Add to MANDATE.md |
| Agent prompt injection | None | **DOCS** | Template in MANDATE.md |

### 7. Broker Integration

| Revamp Proposal | Existing Module | Action | Notes |
|---|---|---|---|
| Alpaca adapter | `execution/` | **IMPLEMENT** | `BrokerAdapterPort` already exists |
| Order service | `execution/` | **EXTEND** | Add investment-specific order logic |
| Websocket monitoring | `execution/` | **EXTEND** | Add real-time position tracking |

---

## Summary

### New Bounded Contexts (3)

| Context | Sprint | Purpose |
|---|---|---|
| `investment_workflow/` | 13 | Analyst roles, debate, decision state machine |
| `investment_knowledge/` | 14 | RAG-based research document retrieval |
| `investment_memo/` | 15 | Memo lifecycle, realized return tracking |

### Extended Modules (7)

| Module | Extension | Sprint |
|---|---|---|
| `workflow/` | Investment decision states | 13 |
| `governance/` | Mandate rules, veto workflow | 18 |
| `governance_engine/` | Investment veto states | 18 |
| `portfolio/` | NAV, Sharpe, drawdown endpoints | 16 |
| `risk/` | Sector/concentration limits | 18 |
| `attribution_engine/` | Selection/allocation/beta/residual | 19 |
| `execution/` | Broker adapter implementation | Future |

### Documentation Only (1)

| Area | File | Status |
|---|---|---|
| IDX domain context | `docs/investment_context/` | **DONE** |

### Frontend Extensions (1)

| Module | Extension | Sprint |
|---|---|---|
| `karsa-web/` | CIO dashboard pages | 16-17 |

---

## Dependency Order

```
Phase 0 (DONE): docs/investment_context/
    │
    ▼
Phase 1: investment_workflow/ (new)
    │
    ├──────────────────────┐
    ▼                      ▼
Phase 2: investment_knowledge/ (new)    Phase 3: investment_memo/ (new)
    │                      │
    └──────────┬───────────┘
               │
               ▼
         Phase 4: CIO Dashboard (extend karsa-web/)
               │
               ▼
         Phase 5: Governance (extend governance/)
               │
               ▼
         Phase 6: Attribution (extend attribution_engine/)
               │
               ▼
         Phase 7: IDX Enhancement (docs only)
```
