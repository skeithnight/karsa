# Karsa Web Console Remediation Plan

**Status:** READY
**Source:** Web Console Audit Report (Readiness: 16/100)
**Target:** Virtual Investment Firm Operating System (80+)
**Principle:** Wire real data first, then add capabilities.

---

## Phase 0: Wire Real Data (Week 1)

**Goal:** Eliminate all stub data. Every page must show real data or explicit empty state.

### Task 0.1: Wire analysts page to real data

**Problem:** `useAnalystsMetrics()` returns hardcoded `{data: []}`.

**Solution:** Connect to `/workers/metrics` endpoint (already exists).

**File:** `karsa-web/src/hooks/analysts/index.ts`
**Impact:** Analysts page shows real worker metrics
**Effort:** 30 minutes

### Task 0.2: Wire performance page to real data

**Problem:** `usePerformanceAttribution()` returns hardcoded `{data: []}`.

**Solution:** Connect to `/performance/attribution` endpoint (already exists).

**File:** `karsa-web/src/hooks/performance/index.ts`
**Impact:** Performance page shows real attribution data
**Effort:** 30 minutes

### Task 0.3: Wire research page to real data

**Problem:** `useListResearchReports()` returns hardcoded `{data: [], total: 0}`.

**Solution:** Connect to `/research/reports` endpoint (already exists).

**File:** `karsa-web/src/hooks/research/index.ts`
**Impact:** Research page shows real reports
**Effort:** 30 minutes

### Task 0.4: Wire infrastructure page to real data

**Problem:** Infrastructure page shows hardcoded status strings.

**Solution:** Create `/api/infrastructure/status` endpoint that returns real system health data.

**Files:**
- `src/karsa/infrastructure/api.py` — new endpoint
- `karsa-web/src/hooks/infrastructure/index.ts` — new hook
- `karsa-web/src/app/infrastructure/page.tsx` — use hook instead of hardcoded data

**Impact:** Infrastructure page shows real system health
**Effort:** 2 hours

### Task 0.5: Fix negative cash balance

**Problem:** `/portfolio/summary` returns `cash_balance: "-300000.0"`.

**Solution:** Fix the portfolio summary calculation.

**Files:** `src/karsa/portfolio/api.py`
**Impact:** Portfolio shows correct cash balance
**Effort:** 1 hour

---

## Phase 1: Data Freshness & Export (Week 2)

**Goal:** Add data freshness indicators and export capability.

### Task 1.1: Add data freshness indicators

**Problem:** No page shows when data was last updated.

**Solution:** Add `last_updated` timestamp to all API responses. Show "Updated X ago" on all pages.

**Files:**
- All `api/endpoints/*.ts` files
- All page components — add freshness indicator

**Impact:** Users know how fresh the data is
**Effort:** 1 day

### Task 1.2: Add export functionality

**Problem:** No export capability anywhere.

**Solution:** Add CSV export to all DataTable instances.

**Files:**
- `karsa-web/src/components/grid/DataTable.tsx` — add export button
- `karsa-web/src/lib/export.ts` — CSV generation utility

**Impact:** Users can export data for external analysis
**Effort:** 1 day

### Task 1.3: Add data freshness indicators to CIO dashboard

**Solution:** Show "Last updated: X seconds ago" on CIO dashboard cards.

**Files:** `karsa-web/src/app/cio-dashboard/page.tsx`
**Impact:** CIO knows data freshness
**Effort:** 30 minutes

---

## Phase 2: Drill-Down & Investigation (Week 3-4)

**Goal:** Enable investigation paths from metrics to supporting data.

### Task 2.1: Add drill-down from portfolio summary

**Problem:** Clicking NAV or sector doesn't drill into holdings.

**Solution:** Make MetricCards clickable. Clicking sector → sector holdings table.

**Files:**
- `karsa-web/src/components/shared/MetricCard.tsx` — add onClick
- `karsa-web/src/app/portfolio/page.tsx` — add drill-down views
- `karsa-web/src/app/portfolio/holdings/page.tsx` — new page

**Impact:** Users can investigate portfolio composition
**Effort:** 2 days

### Task 2.2: Add drill-down from CIO dashboard

**Problem:** Decision cards are display-only. No click action.

**Solution:** Make decision cards clickable. Clicking → full decision detail with memo, debate, analyst scores.

**Files:**
- `karsa-web/src/app/cio-dashboard/page.tsx` — add click handlers
- `karsa-web/src/app/cio-dashboard/decisions/[id]/page.tsx` — new detail page

**Impact:** CIO can investigate decisions
**Effort:** 2 days

### Task 2.3: Add drill-down from performance attribution

**Problem:** Attribution table shows numbers but no supporting detail.

**Solution:** Clicking a row → detailed attribution breakdown with holdings.

**Files:**
- `karsa-web/src/app/performance/page.tsx` — add row click
- `karsa-web/src/app/performance/[date]/page.tsx` — new detail page

**Impact:** Users can understand attribution drivers
**Effort:** 2 days

### Task 2.4: Add drill-down from oversight

**Problem:** Post-mortem list has no detail view.

**Solution:** Clicking a row → full post-mortem detail with root cause analysis.

**Files:**
- `karsa-web/src/app/oversight/page.tsx` — add row click
- `karsa-web/src/app/oversight/[id]/page.tsx` — new detail page

**Impact:** Users can investigate governance failures
**Effort:** 1 day

---

## Phase 3: Investment Workflow (Week 5-7)

**Goal:** Implement end-to-end investment decision workflow.

### Task 3.1: Create investment decision page

**Problem:** No page supports Research → Thesis → Forecast → Decision workflow.

**Solution:** Create `/investments` page with full decision lifecycle.

**Files:**
- `karsa-web/src/app/investments/page.tsx` — decision list
- `karsa-web/src/app/investments/[id]/page.tsx` — decision detail
- `karsa-web/src/hooks/investments/index.ts` — hooks
- `karsa-web/src/features/investments/` — types + mappers

**Impact:** Users can track investment decisions end-to-end
**Effort:** 3 days

### Task 3.2: Wire investment workflow backend

**Solution:** Connect to `/investments/decisions` endpoint (already exists).

**Files:**
- `karsa-web/src/api/endpoints/investments.ts` — API endpoint
- `karsa-web/src/hooks/investments/index.ts` — hooks

**Impact:** Investment decisions page shows real data
**Effort:** 1 day

### Task 3.3: Add analyst score visualization to decisions

**Solution:** Show analyst scores (Fundamental, Technical, Sentiment, Risk, Market) on decision detail.

**Files:** `karsa-web/src/app/investments/[id]/page.tsx`
**Impact:** Users can see which analysts contributed to decision
**Effort:** 1 day

### Task 3.4: Add debate visualization to decisions

**Solution:** Show bull/bear debate memos on decision detail.

**Files:** `karsa-web/src/app/investments/[id]/page.tsx`
**Impact:** Users can understand decision rationale
**Effort:** 1 day

---

## Phase 4: Realized Returns & Feedback Loop (Week 8-9)

**Goal:** Close the feedback loop with realized return tracking.

### Task 4.1: Add realized return tracking to memos

**Problem:** No page shows actual vs predicted returns.

**Solution:** Add realized return fields to memo detail. Show target vs actual comparison.

**Files:**
- `karsa-web/src/app/memos/[id]/page.tsx` — new detail page
- `karsa-web/src/hooks/memos/index.ts` — add close position mutation

**Impact:** Users can evaluate prediction accuracy
**Effort:** 2 days

### Task 4.2: Add win rate tracking

**Problem:** No win rate tracking by analyst, strategy, or conviction.

**Solution:** Create `/analytics/win-rates` page with win rate breakdown.

**Files:**
- `karsa-web/src/app/analytics/win-rates/page.tsx` — new page
- `karsa-web/src/hooks/analytics/index.ts` — hooks

**Impact:** Users can evaluate which approaches work
**Effort:** 2 days

### Task 4.3: Add conviction calibration tracking

**Problem:** No way to verify if conviction levels predict outcomes.

**Solution:** Show conviction vs realized return correlation.

**Files:** `karsa-web/src/app/analytics/calibration/page.tsx`
**Impact:** Users can evaluate conviction accuracy
**Effort:** 1 day

---

## Phase 5: Research & Forecast Quality (Week 10-11)

**Goal:** Track research and forecast quality.

### Task 5.1: Add research quality tracking

**Problem:** Cannot evaluate which research generated value.

**Solution:** Link research reports to outcomes. Show research-to-return correlation.

**Files:**
- `karsa-web/src/app/research/[id]/page.tsx` — research detail with outcomes
- `karsa-web/src/app/analytics/research-quality/page.tsx` — quality dashboard

**Impact:** Users can evaluate research value
**Effort:** 3 days

### Task 5.2: Add forecast quality tracking

**Problem:** Cannot evaluate forecast accuracy.

**Solution:** Track forecasts vs outcomes. Show calibration metrics.

**Files:**
- `karsa-web/src/app/analytics/forecast-quality/page.tsx` — quality dashboard
- `karsa-web/src/hooks/analytics/index.ts` — forecast hooks

**Impact:** Users can evaluate forecast accuracy
**Effort:** 3 days

### Task 5.3: Add staleness indicators

**Problem:** No way to know if research or forecasts are stale.

**Solution:** Add "Last updated" and "Staleness" indicators to research and thesis pages.

**Files:**
- `karsa-web/src/app/research/page.tsx`
- `karsa-web/src/app/theses/page.tsx`

**Impact:** Users can identify stale data
**Effort:** 1 day

---

## Phase 6: Observability & Monitoring (Week 12)

**Goal:** Real infrastructure monitoring.

### Task 6.1: Wire infrastructure page to real monitoring

**Problem:** Infrastructure page shows hardcoded data.

**Solution:** Connect to real monitoring endpoints.

**Files:**
- `src/karsa/infrastructure/api.py` — health check endpoints
- `karsa-web/src/app/infrastructure/page.tsx` — use real data

**Impact:** Users can observe system health
**Effort:** 2 days

### Task 6.2: Add data pipeline health indicators

**Solution:** Show projection worker status, outbox queue depth, event processing lag.

**Files:** `karsa-web/src/app/infrastructure/page.tsx`
**Impact:** Users can observe pipeline health
**Effort:** 1 day

### Task 6.3: Add error rate monitoring

**Solution:** Show API error rates, failed events, retry counts.

**Files:** `karsa-web/src/app/infrastructure/page.tsx`
**Impact:** Users can identify processing failures
**Effort:** 1 day

---

## Phase 7: Comparison & Advanced UX (Week 13-14)

**Goal:** Add comparison views and advanced UX.

### Task 7.1: Add thesis comparison view

**Problem:** Cannot compare theses side-by-side.

**Solution:** Multi-select theses → comparison view.

**Files:** `karsa-web/src/app/theses/compare/page.tsx`
**Impact:** Users can compare investment theses
**Effort:** 2 days

### Task 7.2: Add period comparison

**Problem:** Cannot compare performance across periods.

**Solution:** Period selector on performance page.

**Files:** `karsa-web/src/app/performance/page.tsx`
**Impact:** Users can compare MTD/QTD/YTD performance
**Effort:** 1 day

### Task 7.3: Add notification system

**Problem:** No alerts or notifications.

**Solution:** Toast notifications for important events.

**Files:**
- `karsa-web/src/components/shared/NotificationCenter.tsx`
- `karsa-web/src/hooks/notifications/index.ts`

**Impact:** Users are alerted to important events
**Effort:** 2 days

---

## Dependency Graph

```
Phase 0 (Wire Data) ────────────────────────────────┐
  │                                                   │
  ▼                                                   │
Phase 1 (Freshness + Export) ────────────────────┐    │
  │                                              │    │
  ▼                                              ▼    │
Phase 2 (Drill-Down) ────────────┐             │    │
  │                               │             │    │
  ▼                               ▼             ▼    ▼
Phase 3 (Investment Workflow) ◀──────────────────────┘
  │
  ▼
Phase 4 (Realized Returns)
  │
  ▼
Phase 5 (Research & Forecast Quality)
  │
  ▼
Phase 6 (Observability)
  │
  ▼
Phase 7 (Comparison & Advanced UX)
```

---

## Test Targets

| Phase | New Tests | Cumulative |
|---|---|---|
| Phase 0 | 10 | 10 |
| Phase 1 | 15 | 25 |
| Phase 2 | 20 | 45 |
| Phase 3 | 25 | 70 |
| Phase 4 | 15 | 85 |
| Phase 5 | 15 | 100 |
| Phase 6 | 10 | 110 |
| Phase 7 | 15 | 125 |

---

## Success Criteria

| Metric | Current | Target |
|---|---|---|
| Data Integrity | 2/5 | 5/5 |
| Business Logic | 1/5 | 4/5 |
| Investment Workflow | 1/5 | 4/5 |
| UX & Actionability | 2/5 | 4/5 |
| Research Quality | 0/5 | 3/5 |
| Forecast Quality | 0/5 | 3/5 |
| Attribution | 0/5 | 4/5 |
| Governance | 1/5 | 4/5 |
| Observability | 0/5 | 3/5 |
| Gap Analysis | 1/5 | 4/5 |
| **Total** | **16/100** | **80+/100** |

---

## Effort Estimate

| Phase | Duration | Priority |
|---|---|---|
| Phase 0 | 1 week | P0 — Critical |
| Phase 1 | 1 week | P0 — Critical |
| Phase 2 | 2 weeks | P1 — High |
| Phase 3 | 3 weeks | P1 — High |
| Phase 4 | 2 weeks | P1 — High |
| Phase 5 | 2 weeks | P2 — Medium |
| Phase 6 | 1 week | P2 — Medium |
| Phase 7 | 2 weeks | P2 — Medium |
| **Total** | **14 weeks** | |
