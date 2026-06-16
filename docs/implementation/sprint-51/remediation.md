# Sprint-51 Implementation Readiness Remediation

## 1. API Contract Package

### 1.1 `/api/v1/portfolio/summary`
* **Owner Service:** Portfolio Engine
* **Purpose:** High-level CIO snapshot.
* **Pagination/Sorting/Filtering:** N/A (Singleton).
* **Caching:** `staleTime: 60000`, invalidation on WebSocket push.
* **TypeScript Types & Schema:**
```typescript
export interface PortfolioSummaryDTO {
  total_aum: number;
  daily_pnl: number;
  active_theses_count: number;
  net_exposure: number;
  last_updated: string;
}
```
* **Example Response:**
```json
{
  "total_aum": 15000000.00,
  "daily_pnl": 45000.50,
  "active_theses_count": 24,
  "net_exposure": 0.12,
  "last_updated": "2026-06-15T10:00:00Z"
}
```

### 1.2 `/api/v1/portfolio/exposure`
* **Owner Service:** Portfolio Engine
* **Purpose:** Sector/Risk exposure arrays for heatmaps.
* **Pagination:** N/A.
* **TypeScript Types:**
```typescript
export interface SectorExposureDTO { sector: string; allocation_pct: number; }
export interface ExposureHeatmapDTO { sectors: SectorExposureDTO[]; }
```
* **Example Response:**
```json
{
  "sectors": [
    { "sector": "TECHNOLOGY", "allocation_pct": 0.45 },
    { "sector": "HEALTHCARE", "allocation_pct": 0.15 }
  ]
}
```

### 1.3 `/api/v1/research/reports`
* **Owner Service:** Research Engine
* **Purpose:** Chronological intelligence feed.
* **Pagination:** Cursor-based (`?cursor={id}&limit=50`).
* **Filtering:** `?ticker={ticker}&analyst={analyst}`.
* **TypeScript Types:**
```typescript
export interface ResearchReportDTO {
  id: string;
  ticker: string;
  analyst_id: string;
  conviction: "HIGH" | "MED" | "LOW";
  summary: string;
  published_at: string;
}
```

### 1.4 `/api/v1/theses`
* **Owner Service:** Thesis Engine
* **Purpose:** Core ranked table backing AG Grid.
* **Pagination:** Offset-based (`?page=1&size=100`).
* **Sorting:** `?sort=conviction&order=desc`.
* **TypeScript Types:**
```typescript
export interface ThesisListDTO {
  thesis_urn: string;
  ticker: string;
  direction: "LONG" | "SHORT";
  state: "INITIATED" | "ACTIVE" | "INVALIDATED";
  conviction_score: number;
  expected_horizon_days: number;
}
```

### 1.5 `/api/v1/theses/{id}` and `/api/v1/theses/{id}/lineage`
* **Owner Service:** Thesis Engine
* **Purpose:** Single Thesis hub retrieval.
* **TypeScript Types:**
```typescript
export interface ThesisDetailDTO {
  thesis_urn: string;
  ticker: string;
  invalidation_criteria: string[];
}
export interface ThesisLineageDTO {
  source_research_ids: string[];
  decision_urns: string[];
  governance_review_ids: string[];
}
```

### 1.6 `/api/v1/decisions` (Investment Memos)
* **Owner Service:** Decision Engine
* **Purpose:** Read-only intent journal.
* **Pagination:** Offset-based (`?page=1&size=50`).
* **TypeScript Types:**
```typescript
export interface DecisionMemoDTO {
  decision_urn: string;
  thesis_urn: string;
  intent: string;
  pep_signature: string;
  timestamp: string;
}
```

### 1.7 `/api/v1/performance`
* **Owner Service:** Performance Engine
* **Purpose:** Time-series returns and attribution decomposition.
* **Filtering:** `?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`.
* **TypeScript Types:**
```typescript
export interface AttributionDTO {
  date: string;
  selection_return: number;
  allocation_return: number;
  beta_return: number;
}
```

### 1.8 `/api/v1/workers/metrics`
* **Owner Service:** Worker Matrix / Analytics
* **Purpose:** AI Analyst Trust Scores.
* **TypeScript Types:**
```typescript
export interface AnalystMetricDTO {
  analyst_id: string;
  role: string;
  trust_score: number;
  win_rate: number;
  drawdown: number;
}
```

### 1.9 `/api/v1/governance`
* **Owner Service:** Governance Engine
* **Purpose:** Investment Oversight post-mortems.
* **Pagination:** Cursor-based.
* **TypeScript Types:**
```typescript
export interface PostMortemDTO {
  id: string;
  thesis_urn: string;
  failure_reason: string;
  policy_overrides: boolean;
  timestamp: string;
}
```

### 1.10 `/api/v1/search`
* **Owner Service:** API Gateway (Aggregator)
* **Purpose:** Powers `⌘K` Command Palette.
* **Filtering:** `?q={query}`.
* **Caching:** `staleTime: 10000` (10s).
* **TypeScript Types:**
```typescript
export interface SearchResultDTO {
  type: "THESIS" | "RESEARCH" | "ANALYST" | "TICKER";
  id: string;
  label: string;
  route: string;
}
```
* **Example Response:**
```json
[
  { "type": "TICKER", "id": "AAPL", "label": "Apple Inc.", "route": "/theses?ticker=AAPL" },
  { "type": "THESIS", "id": "urn:123", "label": "LONG AAPL", "route": "/theses/urn:123" }
]
```

## 2. Screen State Package

| Screen | Skeleton Design | Empty State | Error State | Retry Behaviour |
|---|---|---|---|---|
| **CIO Dashboard** | 3 fading metric cards, blank sparkline box. | "No active pipeline data available." | Global Error Boundary boundary overlay. | `refetch()` button injected in boundary. |
| **Portfolio** | Tremor Donut chart placeholders. | "No capital allocated." | "Failed to load exposure." | Automatic TanStack Query 3x retry backing off. |
| **Research** | Fading list rows (5 items). | "No research generated today." | Toast notification + Retry button. | SWR fetch triggers on window focus. |
| **Theses** | AG Grid loading overlay. | "No theses match current filters." | Grid overlay: "Error loading data." | API retry button inside Grid overlay. |
| **Thesis Detail** | 3-column fading layout. | N/A (404 applies if missing). | 404 Fallback layout. | Redirect to `/theses`. |
| **Memos** | List of fading card headers. | "No memos generated." | Inline alert box. | Auto-retry. |
| **Performance** | Blank Recharts axis grid. | "Insufficient performance data." | Inline alert box. | Manual retry link. |
| **Analysts** | Table skeleton. | "No analysts active." | Inline alert box. | Manual retry link. |
| **Oversight** | Table skeleton. | "Zero compliance events." | Inline alert box. | Manual retry link. |

* **403 State**: Global redirect to `/unauthorized` layout.
* **404 State**: Standard Next.js `not-found.tsx` rendering "Entity not found in CQRS projections".

## 3. State Management Package

| State Category | Definition | Owner | Persistence | Refresh Trigger | Invalidation Trigger | Cache Policy | Recovery |
|---|---|---|---|---|---|---|---|
| **Server State** | API data (Theses, Portfolios) | TanStack Query | Memory | Window Focus | Explicit Mutation | `staleTime: 60s` | Auto-refetch |
| **Client State** | UI Preferences (Theme, Sidebar) | Zustand | LocalStorage | N/A | N/A | Infinite | N/A |
| **URL State** | Pagination, Sort order, Active filters | Next.js Router | URL String | Navigation | Navigation | N/A | Browser History |
| **Session State** | JWT Token | Auth Provider | Cookie (HttpOnly) | Route Change | Token Expiry | N/A | Force Logout |
| **Derived State** | Grouped metrics (e.g., sum of allocations) | React `useMemo` | Memory | Prop Change | Dependency Array | Component Lifecycle | Recalculate |

## 4. Dependency Matrix
**Screen dependencies:**
* `CIO Dashboard` -> `<MetricCard>`, `<IntelligenceTimeline>` -> `/api/v1/portfolio/summary`, `/api/v1/research/reports` -> Portfolio, Research Engines
* `Thesis Workspace` -> `<DataTable>` -> `/api/v1/theses` -> Thesis Engine
* `Thesis Detail` -> `<LineageTree>` -> `/api/v1/theses/{id}/lineage` -> Thesis Engine

**Story Dependencies (Critical Path):**
* **WP-1** (Foundation) -> **Blocks** -> **WP-2** (Layout) -> **Blocks** -> All View Implementation.
* **WP-6** (Frontend Foundation Library) -> **Blocks** -> **WP-4** (Thesis Workspace).

## 5. Work Breakdown Structure
* **Epic: Core Foundation**
  * **Feature**: Boilerplate
    * *Task 1*: Initialize Next.js Static Export. (Complexity: 1)
    * *Task 2*: Install shadcn/ui & Tailwind. (Complexity: 1)
  * **Feature**: Shared Library
    * *Task 3*: Build `DataTable` AG Grid wrapper. (Complexity: 3)
    * *Task 4*: Build `MetricCard` Tremor wrapper. (Complexity: 2)
* **Epic: Data Layer**
  * **Feature**: API Contracts
    * *Task 5*: Generate TypeScript DTO interfaces. (Complexity: 2)
    * *Task 6*: Scaffold TanStack Query fetchers. (Complexity: 3)
* **Epic: Operations Views**
  * **Feature**: CIO Dashboard
    * *Task 7*: Assemble Summary hooks. (Complexity: 3)
    * *Task 8*: Assemble Intelligence Timeline. (Complexity: 3)
  * **Feature**: Thesis Hub
    * *Task 9*: Implement Thesis AG Grid Workspace. (Complexity: 5)
    * *Task 10*: Implement Hub-and-Spoke Detail Page. (Complexity: 5)
* **Epic: Production Readiness**
  * **Feature**: Nginx
    * *Task 11*: Write multi-stage Dockerfile. (Complexity: 2)

## 6. Frontend Foundation Package
* `<DataTable>`: AG Grid React wrapper. Props: `columnDefs`, `rowData`, `onSortChanged`. Reusability: High (Theses, Analysts, Memos).
* `<MetricCard>`: Tremor Card. Props: `title`, `metric`, `delta`, `statusType`. Reusability: High (Dashboard, Portfolio).
* `<PageHeader>`: shadcn block. Props: `title`, `breadcrumbs`, `actionSlot`. Reusability: Very High.
* `<EmptyState>`: Centered SVG + Text. Props: `icon`, `message`, `retryAction`. Reusability: Very High.
* `<SearchCommandPalette>`: shadcn Command component. Props: `open`, `setOpen`. Consumer: GlobalHeader.

## 7. RBAC Completion Package
* **403 Handling**: TanStack Query global `onError` interceptor catches HTTP 403. Uses Next.js router to push to `/403`.
* **Unauthorized Behaviour**: User sees "Operator Authorization Required" and is prompted to refresh token.
* **Hidden Navigation**: `GlobalSidebar` maps an array of routes. Routes verify `allowedRoles` against the decoded JWT before rendering the `<Link>`.
* **Route Guards**: Next.js App Router Middleware intercepts static navigation. If token is missing, redirect to `/`.
* **Widget Guards**: Specific components (e.g., Overrides) wrapped in `<RoleGuard allowed={["ADMIN"]}>`.
* **Session Expiration**: API interceptor catches HTTP 401. Zustand store clears, UI forces hard reload.

## 8. Remaining Risks
* **None Critical.** The missing JSON contracts and type definitions have been explicitly provided in Section 1. The ambiguous UI states (loading, empty) are fully defined in Section 2. The dependency matrix defines the exact critical path for unblocking frontend developers.

## 9. Updated Readiness Assessment
The required execution artifacts have been fully synthesized to align with the Virtual Investment Firm product vision without modifying the frozen architecture.

**Final Verdict: IMPLEMENTATION_READY**
