# Sprint-63: Remediation Plan

Status: COMPLETE
Date: 2026-06-24

## Remediation Items (from Audit)

### R1: Fix Brinson Double-Prefix Bug [P0]

**File:** `karsa-web/src/api/endpoints/performance.ts`
**Issue:** `getBrinsonAttribution` path is `/api/v1/attribution/brinson`. Base URL already prepends `/api`, producing `/api/api/v1/attribution/brinson`.
**Fix:** Change path to `/v1/attribution/brinson`.
**Effort:** 1 line change.

---

### R2: Create CIO Dashboard API Client Functions [P0]

**File:** NEW `karsa-web/src/api/endpoints/cio-dashboard.ts`

The CIO Dashboard backend module (`src/karsa/cio_dashboard/api/routes.py`) has 10 endpoints. The frontend has zero API client functions for them.

| Function | Method | Path | Returns |
|----------|--------|------|---------|
| `getPortfolioSummary()` | GET | `/api/portfolio/summary` | NAV, holdings, cash |
| `getHoldings()` | GET | `/api/portfolio/holdings` | Holdings list |
| `getRiskTrafficLight()` | GET | `/api/risk/traffic-light` | Volatility, beta, concentration |
| `getDecisionsToday()` | GET | `/api/decisions/today` | Today's decisions |
| `getLatestDecision(ticker)` | GET | `/api/decisions/{ticker}/latest` | Latest decision for ticker |
| `getSectorAllocation()` | GET | `/api/risk/sector-allocation` | Sector allocation |
| `getPerformanceAttribution()` | GET | `/api/performance/attribution` | Attribution breakdown |
| `getConglomerateExposure()` | GET | `/api/exposures/conglomerates` | IDX group exposures |
| `getEquityCurve()` | GET | `/api/cio/portfolio/equity-curve` | Equity curve timeseries |
| `getSectorExposure()` | GET | `/api/cio/exposures/sectors` | Sector exposure |

**Effort:** ~120 lines.

---

### R3: Create Investment Workflow API Client Functions [P0]

**File:** NEW `karsa-web/src/api/endpoints/investments.ts`

| Function | Method | Path | Returns |
|----------|--------|------|---------|
| `approveDecision(id)` | POST | `/investments/decisions/{id}/approve` | Decision result |
| `rejectDecision(id)` | POST | `/investments/decisions/{id}/reject` | Decision result |

**Effort:** ~40 lines.

---

### R4: Create 12 New React Query Hooks [P0]

**Files:**

NEW `karsa-web/src/hooks/dashboard/index.ts`:
- `useRiskTrafficLight()` → `GET /api/risk/traffic-light`
- `useEquityCurve()` → `GET /api/cio/portfolio/equity-curve`
- `usePositions()` → `GET /api/portfolio/holdings`
- `useSectorExposure()` → `GET /api/cio/exposures/sectors`
- `useConglomerateExposure()` → `GET /api/exposures/conglomerates`

NEW `karsa-web/src/hooks/signals/index.ts`:
- `useSignals()` → merges `useTheses()` + `useMemos()` into unified SignalVM
- `useApproveSignal()` → mutation hook for approve
- `useRejectSignal()` → mutation hook for reject

EXTEND `karsa-web/src/hooks/performance/index.ts`:
- `useBrinsonAttribution()` → `GET /api/v1/attribution/brinson` (fixed path)
- `useCalibration()` → `GET /performance/brier-scores` + conviction tier aggregation

NEW `karsa-web/src/hooks/governance/index.ts`:
- `useMandateChecks()` → aggregation from risk + governance endpoints
- `useInfrastructureStatus()` → `GET /health` + capability health checks

**Effort:** ~400 lines total.

---

### R5: Create 12 New ViewModel Types + Mappers [P0]

**Files:**

NEW `karsa-web/src/features/dashboard/types/viewmodels.ts`:
- `DashboardKpiVM` — nav, dailyPnl, dailyPnlPct, ytdAlpha, sharpe, maxDD, cash, cashIdle
- `RiskMonitorVM` — var95, volAnn, betaIhsg, conglomerateExposure, maxDD, rupiahWeekly (each with value, status, barPct)
- `EquityCurveVM` — karsa: Point[], ihsg: Point[], period: string
- `PositionVM` — ticker, sector, side, lots, entry, last, mktVal, pnlPct, conviction: 1-5

NEW `karsa-web/src/features/dashboard/utils/mappers.ts`:
- `mapDashboardKpis(portfolio, risk)` — merges portfolio summary + risk traffic-light
- `mapRiskMonitor(risk)` — transforms risk traffic-light response
- `mapEquityCurve(curve)` — transforms equity curve timeseries
- `mapPositions(holdings, theses)` — joins holdings with thesis conviction

NEW `karsa-web/src/features/signals/types/viewmodels.ts`:
- `SignalVM` — ticker, action, status, summary, conviction, target, stop, size, style, thesisId

NEW `karsa-web/src/features/signals/utils/mappers.ts`:
- `mapSignals(theses, decisions)` — merges thesis + decision data into SignalVM

NEW `karsa-web/src/features/portfolio/types/viewmodels.ts` (extend existing):
- `SectorExposureVM` — sector, pctNav
- `ConglomerateExposureVM` — name, exposurePct, limitPct, status

NEW `karsa-web/src/features/portfolio/utils/mappers.ts` (extend existing):
- `mapSectorExposure(data)` — transforms sector allocation
- `mapConglomerateExposure(data)` — transforms conglomerate data with limit checks

NEW `karsa-web/src/features/performance/types/viewmodels.ts` (extend existing):
- `PerformanceKpiVM` — ytdReturn, selectionAlpha, allocationAlpha, betaDrag, brierScore, winRate
- `BrinsonAttributionVM` — period, selection, allocation, beta, residual, total, winRate
- `CalibrationVM` — tier, winPct, count, target

NEW `karsa-web/src/features/performance/utils/mappers.ts` (extend existing):
- `mapPerformanceKpis(attribution, brier)` — merges attribution + brier data
- `mapBrinsonAttribution(data)` — transforms brinson response
- `mapCalibration(brierScores, theses)` — aggregates by conviction tier

NEW `karsa-web/src/features/governance/types/viewmodels.ts` (extend existing):
- `MandateCheckVM` — rule, status, value
- `InfrastructureStatusVM` — service, status, note

NEW `karsa-web/src/features/governance/utils/mappers.ts` (extend existing):
- `mapMandateChecks(risk, governance)` — aggregates compliance data
- `mapInfrastructureStatus(health, capabilities)` — aggregates service health

**Effort:** ~600 lines total.

---

### R6: Create 12 New UI Components [P1]

| Component | File | Purpose |
|-----------|------|---------|
| `AppShell` | `components/layout/AppShell.tsx` | Top-level shell with top-tab bar + ticker tape |
| `TopTabBar` | `components/layout/TopTabBar.tsx` | 5-tab navigation bar |
| `TickerTape` | `components/shared/TickerTape.tsx` | Live market ticker strip |
| `WibClock` | `components/shared/WibClock.tsx` | WIB timezone clock |
| `KpiStrip` | `components/shared/KpiStrip.tsx` | Row of KPI cards with delta |
| `ConvictionPips` | `components/shared/ConvictionPips.tsx` | 5-dot conviction indicator |
| `RiskPanel` | `components/shared/RiskPanel.tsx` | Risk monitor with bar indicators |
| `SectorBars` | `components/shared/SectorBars.tsx` | Horizontal sector exposure bars |
| `ConglomerateHeatmap` | `components/shared/ConglomerateHeatmap.tsx` | Conglomerate limit grid |
| `BrierCalibration` | `components/shared/BrierCalibration.tsx` | Brier score bar chart by tier |
| `MandateChecklist` | `components/shared/MandateChecklist.tsx` | Compliance pass/warn/fail list |
| `InfrastructurePanel` | `components/shared/InfrastructurePanel.tsx` | Service health status grid |

**Effort:** ~800 lines total.

---

### R7: Create 5 Page Components [P1]

| Page | File | Replaces |
|------|------|----------|
| `DashboardPage` | `app/(dashboard)/page.tsx` | `app/page.tsx` + `app/cio-dashboard/page.tsx` + `app/analytics/page.tsx` |
| `SignalsPage` | `app/(signals)/page.tsx` | NEW (merges theses + memos) |
| `PortfolioPage` | `app/(portfolio)/page.tsx` | `app/portfolio/page.tsx` |
| `PerformancePage` | `app/(performance)/page.tsx` | `app/performance/page.tsx` |
| `GovernancePage` | `app/(governance)/page.tsx` | `app/oversight/page.tsx` + `app/infrastructure/page.tsx` |

**Effort:** ~500 lines total.

---

### R8: Update Navigation Config [P1]

**File:** `karsa-web/src/config/navigation.ts`

Replace 15 flat nav items with 5 top-level tabs:

```typescript
export const NAV_TABS = [
  { label: 'Dashboard', href: '/', icon: 'LayoutDashboard' },
  { label: 'Signals', href: '/signals', icon: 'Bolt' },
  { label: 'Portfolio', href: '/portfolio', icon: 'ChartPie' },
  { label: 'Performance', href: '/performance', icon: 'TrendingUp' },
  { label: 'Governance', href: '/governance', icon: 'ShieldCheck' },
]
```

**Effort:** ~30 lines.

---

### R9: Extend Thesis DTOs [P2]

**Backend file:** `src/karsa/thesis/api/router.py`
**Issue:** Prototype shows target, stop, size, style fields not in thesis API response.
**Action:** Check if these exist in domain model. If yes, add to projection. If no, defer.

**Effort:** TBD (depends on domain model inspection).

---

### R10: New Governance Endpoint [P2]

**Backend file:** NEW `src/karsa/governance_engine/api.py` or extend existing
**Endpoint:** `GET /governance/mandate-checks`
**Alternative:** Aggregate from existing `GET /risk/evaluations` + `GET /intelligence/governance/suspensions` in frontend mapper.

**Recommendation:** Start with frontend aggregation. Build dedicated endpoint only if aggregation is too slow.

**Effort:** 0 lines (frontend aggregation) or ~100 lines (new endpoint).

---

## Execution Order

```
Phase 1 (Bug Fix):        R1 — Fix Brinson double-prefix
Phase 2 (API Layer):      R2 — CIO Dashboard API client
                          R3 — Investment API client
Phase 3 (Hooks):          R4 — 12 React Query hooks
Phase 4 (View Models):    R5 — 12 ViewModel types + mappers
Phase 5 (Components):     R6 — 12 new UI components
Phase 6 (Pages):          R7 — 5 page components
Phase 7 (Navigation):     R8 — Update nav config
Phase 8 (Optional):       R9 — Extend thesis DTOs
                          R10 — Governance endpoint
```

## Dependencies

```
R1 ──→ R4 (Brinson hook needs fixed path)
R2 ──→ R4 (hooks need API client functions)
R3 ──→ R4 (approve/reject hooks need API client)
R4 ──→ R5 (mappers need hook return types)
R5 ──→ R6 (components need ViewModel types)
R6 ──→ R7 (pages need components)
R7 ──→ R8 (pages need nav config)
```

## Estimated Effort

| Phase | Lines of Code | Files Changed | Files Created |
|-------|--------------|---------------|---------------|
| R1: Bug fix | 1 | 1 | 0 |
| R2: API client | 120 | 0 | 1 |
| R3: API client | 40 | 0 | 1 |
| R4: Hooks | 400 | 1 | 2 |
| R5: ViewModels | 600 | 4 | 4 |
| R6: Components | 800 | 0 | 12 |
| R7: Pages | 500 | 5 | 5 |
| R8: Navigation | 30 | 1 | 0 |
| **Total** | **~2,500** | **12** | **25** |
