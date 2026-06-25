# Sprint-63: Audit — API Endpoint Gap Analysis

Status: COMPLETE
Date: 2026-06-24

## Methodology

For each page in the design prototype (`docs/revamp/karsa_console_revamp.html`), we audited:
1. What data the prototype UI requires
2. Which backend endpoints exist to serve that data
3. Which frontend API client functions exist
4. What gaps remain (missing endpoints, missing frontend hooks, bugs)

---

## 1. Dashboard Page (`/`)

Prototype requires: KPI strip (NAV, PnL, Alpha, Sharpe, Max DD, Cash), equity curve vs IHSG, risk monitor (6 metrics with bar indicators), open positions table with conviction pips.

### 1.1 KPI Strip

| KPI | Backend Endpoint | Status | Frontend Hook | Notes |
|-----|-----------------|--------|---------------|-------|
| NAV | `GET /api/portfolio/summary` (CIO Dashboard) | ✅ EXISTS | `usePortfolioSummary()` | Returns `total_aum` |
| Daily PnL | `GET /api/portfolio/summary` | ✅ EXISTS | `usePortfolioSummary()` | Returns `daily_pnl` |
| YTD Alpha | `GET /api/performance/attribution` | ✅ EXISTS | `usePerformanceAttribution()` | Needs aggregation logic |
| Sharpe | `GET /api/risk/traffic-light` | ✅ EXISTS | ❌ NO HOOK | Frontend has no hook for traffic-light |
| Max DD | `GET /api/risk/traffic-light` | ✅ EXISTS | ❌ NO HOOK | Same as above |
| Cash | `GET /api/portfolio/summary` | ✅ EXISTS | `usePortfolioSummary()` | Returns cash balance |

**Gap:** `useRiskTrafficLight()` hook does not exist. Frontend needs a new hook hitting `GET /api/risk/traffic-light`.

### 1.2 Equity Curve

| Data | Backend Endpoint | Status | Frontend Hook | Notes |
|------|-----------------|--------|---------------|-------|
| Karsa equity curve | `GET /api/cio/portfolio/equity-curve` | ✅ EXISTS | ❌ NO HOOK | CIO Dashboard endpoint exists |
| IHSG benchmark | — | ❌ MISSING | — | No endpoint for benchmark index data |

**Gap:** Need `useEquityCurve()` hook. IHSG benchmark data needs either a new endpoint or client-side fetch from external API (YFinance).

### 1.3 Risk Monitor

| Metric | Backend Endpoint | Status | Frontend Hook | Notes |
|--------|-----------------|--------|---------------|-------|
| VaR 95% | `GET /api/risk/traffic-light` | ✅ EXISTS | ❌ NO HOOK | Returns volatility, beta, concentration |
| Volatility ann. | `GET /api/risk/traffic-light` | ✅ EXISTS | ❌ NO HOOK | |
| Beta vs IHSG | `GET /api/risk/traffic-light` | ✅ EXISTS | ❌ NO HOOK | |
| Conglomerate exposure | `GET /api/exposures/conglomerates` | ✅ EXISTS | ❌ NO HOOK | CIO Dashboard endpoint |
| Max drawdown | `GET /api/risk/traffic-light` | ✅ EXISTS | ❌ NO HOOK | |
| Rupiah weekly | — | ❌ MISSING | — | No FX endpoint |

**Gap:** Need `useRiskMonitor()` hook. FX data (USD/IDR) needs external source or new endpoint.

### 1.4 Open Positions Table

| Data | Backend Endpoint | Status | Frontend Hook | Notes |
|------|-----------------|--------|---------------|-------|
| Positions list | `GET /api/portfolio/holdings` | ✅ EXISTS | ❌ NO HOOK | CIO Dashboard endpoint |
| Conviction | `GET /thesis` | ✅ EXISTS | `useTheses()` | Need to join with positions |
| Sector | `GET /api/risk/sector-allocation` | ✅ EXISTS | ❌ NO HOOK | |

**Gap:** Need `usePositions()` hook hitting `GET /api/portfolio/holdings`. Conviction pips require joining thesis conviction scores with positions.

### 1.5 Ticker Tape

| Data | Backend Endpoint | Status | Frontend Hook | Notes |
|------|-----------------|--------|---------------|-------|
| IHSG index | — | ❌ MISSING | — | External data source needed |
| USD/IDR | — | ❌ MISSING | — | External data source needed |
| Top holdings prices | — | ❌ MISSING | — | No real-time price endpoint |

**Gap:** Ticker tape requires market data. Options: (a) new backend endpoint proxying YFinance/Saham-MCP, (b) client-side fetch to external API, (c) WebSocket from CIO producer.

### Dashboard Summary

| Category | Exists | Missing |
|----------|--------|---------|
| Backend endpoints | 6 | 3 (FX, benchmark, real-time prices) |
| Frontend hooks | 2 | 5 (risk traffic-light, equity curve, positions, sector, conglomerate) |
| Frontend components | 0 | 4 (KpiStrip, RiskPanel, EquityCurve, ConvictionPips) |

---

## 2. Signals Page (`/signals`)

Prototype requires: Merged thesis/memo signal hub with approve/reject workflow, filter tabs, conviction metadata, target/stop/size display.

### 2.1 Signal List (Theses + Memos)

| Data | Backend Endpoint | Status | Frontend Hook | Notes |
|------|-----------------|--------|---------------|-------|
| Theses | `GET /thesis` | ✅ EXISTS | `useTheses()` | Returns ticker, direction, state, conviction_score |
| Memos/Decisions | `GET /cio/decisions` | ✅ EXISTS | `useMemos()` | Returns decision_urn, thesis_urn, intent |
| Research reports | `GET /research/reports` | ✅ EXISTS | `useResearch()` | Returns ticker, conviction, summary |

**Gap:** Need `useSignals()` hook that merges theses + memos into unified SignalVM. The prototype shows data that spans multiple endpoints — need a mapper that joins thesis data with decision data.

### 2.2 Approve/Reject Actions

| Action | Backend Endpoint | Status | Frontend Hook | Notes |
|--------|-----------------|--------|---------------|-------|
| Approve thesis | `POST /investments/decisions/{id}/approve` | ✅ EXISTS | ❌ NO HOOK | Investment workflow endpoint |
| Reject thesis | `POST /investments/decisions/{id}/reject` | ✅ EXISTS | ❌ NO HOOK | Investment workflow endpoint |
| CIO decision | `POST /cio/decisions` | ✅ EXISTS | ❌ NO HOOK | CIO Engine endpoint |

**Gap:** Need `useApproveSignal()` and `useRejectSignal()` mutation hooks.

### 2.3 Missing Data Fields

| Prototype Field | Available From | Notes |
|----------------|---------------|-------|
| `target` price | ❌ MISSING | Not in thesis or memo DTOs |
| `stop` price | ❌ MISSING | Not in thesis or memo DTOs |
| `size` (% NAV) | ❌ MISSING | Not in thesis or memo DTOs |
| `style` (Swing/Position) | ❌ MISSING | Not in thesis or memo DTOs |
| `summary` text | ✅ Research reports | `GET /research/reports` returns summary |

**Gap:** Target, stop, size, and style are not exposed by any existing endpoint. These may exist in the domain model but are not projected to the API layer. Need to extend thesis or decision DTOs.

### Signals Summary

| Category | Exists | Missing |
|----------|--------|---------|
| Backend endpoints | 4 | 0 (but DTOs need extension) |
| Frontend hooks | 3 | 3 (signals merge, approve, reject) |
| DTO fields | — | 4 (target, stop, size, style) |

---

## 3. Portfolio Page (`/portfolio`)

Prototype requires: Full positions table, sector exposure bars, conglomerate exposure heatmap with limit tracking.

### 3.1 Positions Table

| Data | Backend Endpoint | Status | Frontend Hook | Notes |
|------|-----------------|--------|---------------|-------|
| Holdings | `GET /api/portfolio/holdings` | ✅ EXISTS | ❌ NO HOOK | CIO Dashboard endpoint |
| Portfolio summary | `GET /portfolio/summary` | ✅ EXISTS | `usePortfolioSummary()` | |

**Gap:** Need `usePositions()` hook.

### 3.2 Sector Exposure

| Data | Backend Endpoint | Status | Frontend Hook | Notes |
|------|-----------------|--------|---------------|-------|
| Sector allocation | `GET /api/cio/exposures/sectors` | ✅ EXISTS | ❌ NO HOOK | CIO Dashboard endpoint |
| Sector allocation (alt) | `GET /api/risk/sector-allocation` | ✅ EXISTS | ❌ NO HOOK | Risk engine endpoint |
| Portfolio exposure | `GET /portfolio/exposure` | ✅ EXISTS | `usePortfolioExposure()` | Portfolio engine endpoint |

**Gap:** Need `useSectorExposure()` hook. Two endpoints available — prefer CIO Dashboard one for richer data.

### 3.3 Conglomerate Exposure

| Data | Backend Endpoint | Status | Frontend Hook | Notes |
|------|-----------------|--------|---------------|-------|
| Conglomerate heatmap | `GET /api/exposures/conglomerates` | ✅ EXISTS | ❌ NO HOOK | Returns IDX group exposures |

**Gap:** Need `useConglomerateExposure()` hook.

### Portfolio Summary

| Category | Exists | Missing |
|----------|--------|---------|
| Backend endpoints | 4 | 0 |
| Frontend hooks | 1 | 3 (positions, sector, conglomerate) |

---

## 4. Performance Page (`/performance`)

Prototype requires: KPI strip (YTD, Selection α, Allocation α, Beta drag, Brier, Win rate), Brinson attribution table, Brier calibration bars by conviction tier.

### 4.1 Performance KPIs

| KPI | Backend Endpoint | Status | Frontend Hook | Notes |
|-----|-----------------|--------|---------------|-------|
| YTD Return | `GET /performance/attribution` | ✅ EXISTS | `usePerformanceAttribution()` | Needs aggregation |
| Selection α | `GET /api/v1/attribution/brinson` | ⚠️ BUG | ❌ NO HOOK | Double `/api` prefix bug |
| Allocation α | `GET /api/v1/attribution/brinson` | ⚠️ BUG | ❌ NO HOOK | Same bug |
| Beta drag | `GET /api/v1/attribution/brinson` | ⚠️ BUG | ❌ NO HOOK | Same bug |
| Brier score | `GET /performance/brier-scores` | ✅ EXISTS | `useBrierScores()` | Stub data |
| Win rate | `GET /api/v1/attribution/brinson` | ⚠️ BUG | ❌ NO HOOK | Same bug |

**BUG:** `PerformanceApi.getBrinsonAttribution` uses path `/api/v1/attribution/brinson`. The base URL already prepends `/api`, producing `/api/api/v1/attribution/brinson`. Must fix to `/v1/attribution/brinson`.

### 4.2 Brinson Attribution Table

| Data | Backend Endpoint | Status | Frontend Hook | Notes |
|------|-----------------|--------|---------------|-------|
| Period attribution | `GET /api/v1/attribution/brinson` | ⚠️ BUG | ❌ NO HOOK | Returns selection, allocation, beta, residual, total, win_rate |
| Attribution (alt) | `GET /performance/attribution` | ✅ EXISTS | `usePerformanceAttribution()` | Returns date, selection_return, allocation_return, beta_return |

**Gap:** Need `useBrinsonAttribution()` hook. Must fix double-prefix bug first.

### 4.3 Brier Calibration

| Data | Backend Endpoint | Status | Frontend Hook | Notes |
|------|-----------------|--------|---------------|-------|
| Brier scores | `GET /performance/brier-scores` | ✅ EXISTS | `useBrierScores()` | Returns evaluation_sequence, score |
| Calibration by tier | — | ❌ MISSING | — | Need to aggregate by conviction tier |

**Gap:** The prototype shows Brier scores grouped by STRONG/MEDIUM/WEAK tiers. The backend returns raw scores. Need either backend aggregation or frontend mapper that joins with conviction data from theses.

### Performance Summary

| Category | Exists | Missing |
|----------|--------|---------|
| Backend endpoints | 3 | 0 (but 1 has bug) |
| Frontend hooks | 2 | 3 (risk traffic-light, brinson, calibration) |
| Bugs | 1 | Double `/api` prefix in Brinson path |

---

## 5. Governance Page (`/governance`)

Prototype requires: Mandate compliance checklist, infrastructure status dashboard.

### 5.1 Mandate Compliance

| Data | Backend Endpoint | Status | Frontend Hook | Notes |
|------|-----------------|--------|---------------|-------|
| Governance policies | `GET /intelligence/governance/suspensions` | ✅ EXISTS | ❌ NO HOOK | Returns suspension data |
| Risk evaluations | `GET /risk/evaluations/{id}` | ✅ EXISTS | ❌ NO HOOK | Requires evaluation_id |
| Post-mortems | `GET /post-mortem/records` | ✅ EXISTS | `usePostMortems()` | |
| CIO decisions | `GET /cio/decisions` | ✅ EXISTS | `useMemos()` | |

**Gap:** No single endpoint returns mandate compliance checklist. The prototype shows rules like "IDX-listed only", "Market cap > IDR 5T", "Max position 3% NAV", etc. These are governance policies evaluated by the Governance Engine but not exposed as a checklist API. Need either:
- New endpoint `GET /governance/mandate-checks` that runs compliance checks
- Frontend aggregation from risk evaluations + governance suspensions

### 5.2 Infrastructure Status

| Data | Backend Endpoint | Status | Frontend Hook | Notes |
|------|-----------------|--------|---------------|-------|
| Health check | `GET /health` | ✅ EXISTS | ❌ NO HOOK | Returns db, object_store status |
| Capability health | `GET /capabilities/{family_id}/health` | ✅ EXISTS | ❌ NO HOOK | Per-capability health |
| YFinance connector | — | ❌ MISSING | — | No connector health endpoint |
| Saham-MCP | — | ❌ MISSING | — | No connector health endpoint |
| RAG / pgvector | — | ❌ MISSING | — | No health endpoint |
| LLM pool | — | ❌ MISSING | — | No health endpoint |

**Gap:** The prototype shows 8 infrastructure services. Only `GET /health` exists for general health. Need a consolidated infrastructure status endpoint or frontend that checks multiple endpoints.

### Governance Summary

| Category | Exists | Missing |
|----------|--------|---------|
| Backend endpoints | 4 | 2 (mandate checks, infrastructure status) |
| Frontend hooks | 1 | 3 (mandate, infrastructure, governance) |

---

## 6. Cross-Cutting Issues

### 6.1 Bugs to Fix

| Issue | Location | Severity | Fix |
|-------|----------|----------|-----|
| Double `/api` prefix | `api/endpoints/performance.ts` line with `getBrinsonAttribution` | HIGH | Change path from `/api/v1/attribution/brinson` to `/v1/attribution/brinson` |
| Inconsistent pluralization | `api/endpoints/theses.ts` — `/thesis` vs `/theses` | LOW | Standardize to `/thesis` (matches backend) |
| Shadowed MetricCard | `app/cio-dashboard/page.tsx` | MEDIUM | Delete inline component, use shared `MetricCard` |

### 6.2 Missing Backend Endpoints (Must Build)

| Endpoint | Purpose | Priority | Module |
|----------|---------|----------|--------|
| `GET /api/risk/traffic-light` | Risk metrics for dashboard | HIGH | CIO Dashboard (already exists!) |
| `GET /api/portfolio/holdings` | Holdings list | HIGH | CIO Dashboard (already exists!) |
| `GET /api/cio/portfolio/equity-curve` | Equity curve timeseries | HIGH | CIO Dashboard (already exists!) |
| `GET /api/cio/exposures/sectors` | Sector exposure | HIGH | CIO Dashboard (already exists!) |
| `GET /api/exposures/conglomerates` | Conglomerate heatmap | HIGH | CIO Dashboard (already exists!) |
| `GET /api/decisions/today` | Today's decisions | MEDIUM | CIO Dashboard (already exists!) |
| `GET /governance/mandate-checks` | Compliance checklist | MEDIUM | Governance Engine (NEW) |
| `GET /infrastructure/status` | Service health matrix | LOW | Core (NEW) |

**Key finding:** The CIO Dashboard module already has most endpoints needed! The frontend just isn't using them.

### 6.3 Missing Frontend API Client Functions

| Function | Endpoint | Module |
|----------|----------|--------|
| `CioDashboardApi.getRiskTrafficLight()` | `GET /api/risk/traffic-light` | NEW |
| `CioDashboardApi.getHoldings()` | `GET /api/portfolio/holdings` | NEW |
| `CioDashboardApi.getEquityCurve()` | `GET /api/cio/portfolio/equity-curve` | NEW |
| `CioDashboardApi.getDecisionsToday()` | `GET /api/decisions/today` | NEW |
| `CioDashboardApi.getSectorExposure()` | `GET /api/cio/exposures/sectors` | NEW |
| `CioDashboardApi.getConglomerateExposure()` | `GET /api/exposures/conglomerates` | NEW |
| `InvestmentApi.approveDecision()` | `POST /investments/decisions/{id}/approve` | NEW |
| `InvestmentApi.rejectDecision()` | `POST /investments/decisions/{id}/reject` | NEW |

### 6.4 Missing Frontend Hooks

| Hook | Data Source | Page |
|------|-----------|------|
| `useRiskTrafficLight()` | `GET /api/risk/traffic-light` | Dashboard |
| `useEquityCurve()` | `GET /api/cio/portfolio/equity-curve` | Dashboard |
| `usePositions()` | `GET /api/portfolio/holdings` | Dashboard, Portfolio |
| `useSectorExposure()` | `GET /api/cio/exposures/sectors` | Portfolio |
| `useConglomerateExposure()` | `GET /api/exposures/conglomerates` | Portfolio |
| `useDecisionsToday()` | `GET /api/decisions/today` | Signals |
| `useApproveSignal()` | `POST /investments/decisions/{id}/approve` | Signals |
| `useRejectSignal()` | `POST /investments/decisions/{id}/reject` | Signals |
| `useBrinsonAttribution()` | `GET /api/v1/attribution/brinson` | Performance |
| `useCalibration()` | `GET /performance/brier-scores` + join | Performance |
| `useMandateChecks()` | NEW endpoint needed | Governance |
| `useInfrastructureStatus()` | `GET /health` + capabilities | Governance |

### 6.5 Missing Frontend ViewModels

| ViewModel | Mapper Source | Page |
|-----------|-------------|------|
| `DashboardKpiVM` | Portfolio summary + risk traffic-light | Dashboard |
| `RiskMonitorVM` | Risk traffic-light response | Dashboard |
| `EquityCurveVM` | Equity curve timeseries | Dashboard |
| `PositionVM` | Holdings + theses join | Dashboard, Portfolio |
| `SignalVM` | Theses + decisions merge | Signals |
| `SectorExposureVM` | Sector allocation | Portfolio |
| `ConglomerateExposureVM` | Conglomerate exposure | Portfolio |
| `PerformanceKpiVM` | Attribution + Brier | Performance |
| `BrinsonAttributionVM` | Brinson attribution | Performance |
| `CalibrationVM` | Brier scores aggregated | Performance |
| `MandateCheckVM` | Governance checks | Governance |
| `InfrastructureStatusVM` | Health + capabilities | Governance |

---

## 7. Gap Summary Matrix

### By Page

| Page | Backend Endpoints | Frontend Hooks | Frontend VMs | Components |
|------|------------------|----------------|--------------|------------|
| Dashboard | 6 exist, 0 new | 2 exist, 5 new | 4 new | 4 new |
| Signals | 4 exist, 0 new | 3 exist, 3 new | 1 new | 2 new |
| Portfolio | 4 exist, 0 new | 1 exist, 3 new | 2 new | 2 new |
| Performance | 3 exist (1 buggy) | 2 exist, 3 new | 3 new | 2 new |
| Governance | 4 exist, 2 new | 1 exist, 3 new | 2 new | 2 new |
| **Total** | **21 exist, 2 new** | **9 exist, 17 new** | **12 new** | **12 new** |

### By Priority

**P0 — Must Have (blocks sprint):**
- Fix double `/api` prefix bug in Brinson attribution
- Create 8 new frontend API client functions for existing CIO Dashboard endpoints
- Create 12 new React Query hooks
- Create 12 new ViewModel types + mappers

**P1 — Should Have:**
- New `GET /governance/mandate-checks` endpoint
- Extend thesis DTOs with target/stop/size/style fields
- Create 12 new UI components (KpiStrip, ConvictionPips, etc.)

**P2 — Nice to Have:**
- New `GET /infrastructure/status` consolidated endpoint
- External market data integration for ticker tape (IHSG, USD/IDR, prices)
- Real-time WebSocket updates for risk monitor

---

## 8. Recommendations

1. **Prioritize WS1 (Shell & Nav)** — The top-tab navigation is the foundation. Build `AppShell`, `TopTabBar`, `TickerTape`, and `WibClock` first.

2. **Leverage existing CIO Dashboard endpoints** — Most data for Dashboard and Portfolio pages already exists in `src/karsa/cio_dashboard/api/routes.py`. The frontend just needs hooks and mappers.

3. **Fix the Brinson bug first** — The double `/api` prefix is a 1-line fix that unblocks the entire Performance page.

4. **Defer ticker tape market data** — External data (IHSG, USD/IDR, live prices) requires either a new backend proxy or client-side external API calls. This can be mocked initially.

5. **Extend thesis DTOs** — Target, stop, size, and style fields are needed for the Signals page. Check if these exist in the domain model before adding to the API layer.

6. **Mandate checks as aggregation** — Rather than building a new endpoint, the Governance page can aggregate from existing risk evaluations and governance suspensions endpoints.
