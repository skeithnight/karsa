# Sprint-51 Implementation Execution Package

## 1. Executive Summary
This document provides the definitive, build-authorized engineering execution package for the Sprint-51 Karsa Web Console. It translates the frozen architecture and remediation artifacts into concrete code generation requirements. It establishes the comprehensive Type generation package, React Query data fetching strategies, the precise Next.js App Router repository structure, and a strictly sequenced delivery plan. It ensures engineering can begin implementation immediately without architecture ambiguity.

## 2. Technical Debt Register
| ID | Description | Impact | Severity | Owner | Mitigation | Future Sprint Rec | Arch Impact | Impl Impact | Status |
|---|---|---|---|---|---|---|---|---|---|
| TD-51-01 | Worker ↔ Analyst terminology mapping in API layer. | Confusion between DB 'workers' and UI 'analysts'. | Low | Frontend Team | Create explicit mapping in DTO transformation layer. | Refactor backend API routes in Sprint-52. | None | Minor DTO mapping | OPEN |
| TD-51-02 | Portfolio Summary ownership clarification. | Portfolio API currently aggregates multiple CQRS views. | Med | Backend Team | Accept slightly higher backend latency for `/summary`. | Create dedicated Portfolio Materialized View. | None | StaleTime adjustment | OPEN |
| TD-51-03 | Search API contract expansion. | ⌘K payload lacks context highlights. | Med | Fullstack Team | Render flat search results without text highlighting. | Expand Search Projection to return highlighted spans. | None | Basic UI list only | OPEN |
| TD-51-04 | Intelligence Timeline aggregation strategy. | API requires client-side merging of decisions and reports. | High | Frontend Team | Implement local sorting hook after resolving multiple queries. | Build unified Timeline CQRS projection. | None | CPU load in browser | OPEN |

## 3. Implementation Execution Plan
### Epic: UI Foundation
* **Feature: Project Scaffolding**
  * **Story: WP-1-A**: Initialize Next.js Static Export.
    * *Tasks*: Run `create-next-app`, configure `out/` export, strip unused boilerplate.
    * *Dependencies*: None.
    * *AC/DoD*: `npm run build` generates valid static `out/` directory. (Complexity: 1)
  * **Story: WP-1-B**: Install libraries.
    * *Tasks*: Inject Tailwind, shadcn/ui primitives, Zustand, TanStack Query, AG Grid, Tremor.
    * *Dependencies*: WP-1-A.
    * *AC/DoD*: Library imports resolve without compilation errors. (Complexity: 2)

### Epic: Shared Component Library
* **Feature: Primitives**
  * **Story: WP-2-A**: Build `DataTable` AG Grid Wrapper.
    * *Tasks*: Abstract columnDefs, default sorting, empty state overlays.
    * *Dependencies*: WP-1-B.
    * *AC/DoD*: Reusable grid component mounts with dummy data. (Complexity: 3)
  * **Story: WP-2-B**: Build `MetricCard` Tremor Wrapper.
    * *Tasks*: Wrap Tremor Card + Title + Metric + Delta elements.
    * *Dependencies*: WP-1-B.
    * *AC/DoD*: Dynamic positive/negative delta rendering. (Complexity: 1)

### Epic: Data Access Layer
* **Feature: API Client**
  * **Story: WP-3-A**: Generate DTOs and Query Keys.
    * *Tasks*: Write `types/*.d.ts`, implement fetcher functions.
    * *Dependencies*: WP-1-B.
    * *AC/DoD*: 100% type coverage for API responses. (Complexity: 2)
  * **Story: WP-3-B**: Implement Query Hooks.
    * *Tasks*: Implement `useTheses()`, `useAnalysts()`, etc., with stale-time configs.
    * *Dependencies*: WP-3-A.
    * *AC/DoD*: Hooks return typed `data, isLoading, error` states. (Complexity: 3)

### Epic: Operations Consoles
* **Feature: CIO Dashboard**
  * **Story: WP-4-A**: Build CIO Landing.
    * *Tasks*: Compose `MetricCard` summary, integrate `usePortfolioSummary()`.
    * *Dependencies*: WP-2-B, WP-3-B.
    * *AC/DoD*: Dashboard displays summary metrics. (Complexity: 3)
* **Feature: Thesis Hub**
  * **Story: WP-5-A**: Thesis List.
    * *Tasks*: Mount `DataTable`, integrate `useTheses()`, configure ranking sorts.
    * *Dependencies*: WP-2-A, WP-3-B.
    * *AC/DoD*: AG Grid displays thesis rankings. (Complexity: 5)
  * **Story: WP-5-B**: Thesis Detail Lineage.
    * *Tasks*: Render Hub-and-Spoke layout, fetch lineage dependencies.
    * *Dependencies*: WP-3-B.
    * *AC/DoD*: Detail page visually maps research to outcome. (Complexity: 5)

## 4. Repository Execution Plan
```text
src/
├── app/                  # Next.js Routing
│   ├── (dashboard)/      # Protected Layout Group
│   │   ├── page.tsx      # CIO Dashboard
│   │   ├── theses/
│   │   ├── portfolio/
│   │   ├── analysts/
│   │   ├── oversight/
│   │   ├── research/
│   │   ├── memos/
│   │   ├── performance/
│   │   └── infrastructure/
│   ├── layout.tsx
├── features/             # Domain specific modules
│   ├── theses/
│   ├── portfolio/
│   └── governance/
├── components/           # Shared generic UI
│   ├── ui/               # shadcn atoms
│   ├── shared/           # MetricCard, EmptyState, PageHeader
│   └── grid/             # DataTable (AG Grid)
├── lib/                  # Utilities
│   ├── utils.ts          # Tailwind merge
│   └── formatters.ts     # Currency/Date formatters
├── api/                  # API Clients & Fetchers
│   ├── client.ts         # Axios/Fetch base wrapper
│   └── routes/           # Endpoint specific fetchers
├── hooks/                # TanStack React Query Hooks
│   ├── queries/
│   └── mutations/
├── types/                # DTOs
│   ├── api.d.ts
│   └── models.d.ts
├── state/                # Zustand Stores
│   ├── useUIStore.ts
│   └── useAuthStore.ts
└── test/                 # Vitest / RTL Setup
    ├── setup.ts
    └── mocks/
```

## 5. DTO Package
### 5.1 Shared DTOs
```typescript
export interface PaginationRequestDTO { page: number; size: number; }
export interface PaginationResponseDTO { total_elements: number; total_pages: number; }
export interface ErrorResponseDTO { error_code: string; message: string; timestamp: string; }
```

### 5.2 Portfolio API DTOs
```typescript
// /api/v1/portfolio/summary
export interface PortfolioSummaryResponseDTO {
  total_aum: number;
  daily_pnl: number;
  active_theses_count: number;
  net_exposure: number;
  last_updated: string;
}
```

### 5.3 Thesis API DTOs
```typescript
// /api/v1/theses
export interface ThesisSortDTO { sort_by: "conviction" | "date" | "risk"; direction: "asc" | "desc"; }
export interface ThesisFilterDTO { status?: string; ticker?: string; }
export interface ThesisListResponseDTO {
  data: Array<{
    thesis_urn: string;
    ticker: string;
    direction: "LONG" | "SHORT";
    state: "INITIATED" | "ACTIVE" | "INVALIDATED";
    conviction_score: number;
    expected_horizon_days: number;
  }>;
  pagination: PaginationResponseDTO;
}

// /api/v1/theses/{id}/lineage
export interface ThesisLineageResponseDTO {
  source_research_ids: string[];
  decision_urns: string[];
  governance_review_ids: string[];
}
```

### 5.4 Analyst API DTOs
```typescript
// /api/v1/workers/metrics
export interface AnalystMetricsResponseDTO {
  data: Array<{
    analyst_id: string;
    role: string;
    trust_score: number;
    win_rate: number;
    drawdown: number;
  }>;
}
```

### 5.5 Search API DTOs
```typescript
// /api/v1/search
export interface SearchRequestDTO { q: string; }
export interface SearchResponseDTO {
  results: Array<{ type: "THESIS"|"RESEARCH"|"ANALYST"|"TICKER"; id: string; label: string; route: string; }>;
}
```

## 6. TanStack Query Package
* **Query Keys Strategy**: Organized as arrays. e.g., `['theses', 'list', { page, size, filter }]`
* **Query Hooks**:
  * `usePortfolioSummary()`: Key `['portfolio', 'summary']`. StaleTime: 60s. RefetchInterval: 60s.
  * `useThesesList(params: PaginationRequestDTO & ThesisSortDTO)`: Key `['theses', 'list', params]`. StaleTime: 30s. KeepPreviousData: true.
  * `useThesisLineage(id: string)`: Key `['theses', 'detail', id, 'lineage']`. StaleTime: 5 mins.
  * `useSearch(query: string)`: Key `['search', query]`. Enabled: `query.length >= 2`. StaleTime: 10s.
* **Error Handling Strategy**: Global QueryClient configuration utilizes `onError` boundary to trigger generic toast alerts and log to console. Route-specific errors trigger Error Boundaries.
* **Loading Strategy**: `isLoading` triggers Component-level `LoadingSkeleton`. `isFetching` triggers subtle opacity transitions on lists (AG Grid).
* **Retry Policy**: Default `retry: 3` with exponential backoff.

## 7. UI Foundation Package
* **`DataTable`**: 
  * Props: `columnDefs`, `rowData`, `isLoading`, `onPaginationChange`, `onSortChange`.
  * Consumers: Thesis Workspace, Analysts Workspace, Investment Oversight Workspace.
  * Events: Row click triggers Next.js router push.
* **`MetricCard`**:
  * Props: `title`, `metric`, `subtext`, `deltaPct`, `statusIndicator`.
  * Consumers: CIO Dashboard, Portfolio Console.
* **`PageHeader`**:
  * Props: `title`, `description`, `breadcrumbs`, `children (actions)`.
  * Consumers: All Workspaces.
* **`SearchCommandPalette`**:
  * Props: None (Self-contained state via Zustand global shortcut trigger).
  * Events: `onSelect` router push, `onChange` triggers debounced `useSearch()`.
* **`EmptyState`**:
  * Props: `iconName`, `title`, `description`, `actionLabel`, `onAction`.
  * Consumers: Grids without data, Search without results.
* **`ErrorState`**:
  * Props: `error`, `resetErrorBoundary`.
  * Consumers: React Error Boundary fallback prop.

## 8. Story-to-API Matrix
| Story | Component | API Endpoint | DTO Dependency | Query Hook |
|---|---|---|---|---|
| **WP-4-A** | `CIODashboardPage` | `/api/v1/portfolio/summary` | `PortfolioSummaryResponseDTO` | `usePortfolioSummary()` |
| **WP-5-A** | `ThesisWorkspacePage`| `/api/v1/theses` | `ThesisListResponseDTO` | `useThesesList()` |
| **WP-5-B** | `ThesisDetailPage` | `/api/v1/theses/{id}/lineage` | `ThesisLineageResponseDTO` | `useThesisLineage()` |
| **WP-6** | `AnalystsPage` | `/api/v1/workers/metrics` | `AnalystMetricsResponseDTO` | `useAnalystMetrics()` |
| **WP-3-B** | `CommandPalette` | `/api/v1/search` | `SearchResponseDTO` | `useSearch()` |

* **Critical Path**: Base Fetcher -> DTO -> Query Hook -> Shared Component -> Workspace Page.

## 9. Test Implementation Plan
* **Unit Tests**:
  * *Target*: Date formatters, Currency formatters, Zustand state reducers.
  * *Coverage Expectation*: 90%.
  * *Definition of Done*: `vitest run` passes locally and in CI.
* **Component Tests**:
  * *Target*: `DataTable` rendering empty states, `MetricCard` delta color coding (green vs red).
  * *Coverage Expectation*: 70% critical UI elements.
* **Integration Tests**:
  * *Target*: `useSearch()` debouncing logic against mocked MSW handlers.
* **Contract Tests**: 
  * Skipped for Sprint-51 UI. Trusting backend adherence to provided DTO interfaces.
* **E2E Tests**: 
  * Out of scope for Sprint-51. Operator manual acceptance validation required.

## 10. Delivery Plan
* **Wave 1: Foundation (Days 1-2)**
  * *Objectives*: Next.js App, Nginx Dockerfile, CSS libraries, Routing Skeleton.
  * *Exit Criteria*: Container boots, renders blank navbar, successfully links between 10 dummy routes.
* **Wave 2: Data & State (Days 3-4)**
  * *Objectives*: DTO Definitions, Axios/TanStack Client setup, Mock Service Worker (MSW).
  * *Exit Criteria*: Console logs valid mock DTO responses using React Query.
* **Wave 3: UI Foundation (Days 5-6)**
  * *Objectives*: Implement Shared Components (AG Grid wrappers, Tremor wrappers).
  * *Exit Criteria*: Storybook or generic test page renders complex interactive data grids successfully.
* **Wave 4: Operations Workspaces (Days 7-10)**
  * *Objectives*: Assemble Workspaces mapping Domain Hooks to Foundation Components.
  * *Exit Criteria*: Thesis Hub, Analyst Hub, and Portfolio fully navigable and rendering data.
* **Wave 5: Polish & Deployment (Days 11-14)**
  * *Objectives*: CIO Dashboard integration, Error Boundary injections, Nginx production build.
  * *Exit Criteria*: Complete operator workflow executed without a single `console.error` unhandled exception.

## 11. Readiness Evidence
* **Architecture Compliance**: Wave 1 enforces Nginx static output, satisfying `58-karsa-web-console.md`.
* **Roadmap Compliance**: Story Matrix avoids Watchlist logic, remaining entirely within Sprint-51 bounds.
* **Contract Completeness**: Section 5 details exhaustive TypeScript interfaces mapping directly to API endpoints.
* **Story Completeness**: Delivery Plan explicitly phases the exact Epic breakdown.
* **Testing Completeness**: Test Plan assigns specific frameworks (Vitest, RTL, MSW) to target scopes.
* **Repository Readiness**: Section 4 outlines exact Next.js `src/app` path mapping.

## 12. Remaining Risks
* **Integration Latency**: MSW mocks cannot simulate production AG Grid large-dataset jitter. If the backend cannot perform offset-pagination quickly, UI stuttering may occur. 
* **Mitigation**: Defined `staleTime: 30s` and AG Grid `infiniteRowModel` loading skeleton overrides in UI package to obfuscate query latency.

## 13. Final Build Readiness Verdict
**READY_FOR_IMPLEMENTATION**
