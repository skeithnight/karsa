# Sprint-51 Code Generation Package

## 1. Executive Summary
This document provides the definitive code-generation blueprint for the Sprint-51 Karsa Web Console. Built upon the frozen architecture (`58-karsa-web-console.md`), implementation plan (`plan.md`), remediation package (`remediation.md`), and execution matrix (`implementation.md`), this manifest provides exhaustive instructions for coding agents (Cursor, Copilot, Antigravity) and human engineers. It details exact file paths, explicit DTO-to-ViewModel mapping chains, hook boundaries, and a strict compilation wave sequence to prevent repository drift.

## 2. Implementation Manifest

### WP-1: Project Scaffolding
* **Repository Paths**: `/`
* **Files To Create**: `package.json`, `tsconfig.json`, `next.config.js`, `tailwind.config.ts`, `postcss.config.js`
* **Dependencies**: React, Next.js, Tailwind, shadcn/ui, Zustand, TanStack Query, AG Grid, Tremor.
* **AC/DoD**: `npm run build` succeeds and produces static `out/` directory.

### WP-2: Data Access Layer & DTOs
* **Repository Paths**: `src/api`, `src/types`
* **Files To Create**: `src/api/client.ts`, `src/types/api.d.ts`, `src/types/models.d.ts`
* **Dependencies**: Axios / Fetch API.
* **AC/DoD**: Full TypeScript compilation of domain interfaces.

### WP-3: UI Foundation Library
* **Repository Paths**: `src/components/shared`, `src/components/ui`, `src/components/grid`
* **Files To Create**: `DataTable.tsx`, `MetricCard.tsx`, `PageHeader.tsx`, `EmptyState.tsx`, `ErrorState.tsx`, `LoadingSkeleton.tsx`
* **Dependencies**: AG Grid, Tremor, shadcn/ui primitives.
* **AC/DoD**: Shared components mount in isolation without domain dependencies.

### WP-4: Query Hooks & State
* **Repository Paths**: `src/hooks`, `src/state`
* **Files To Create**: `useUIStore.ts`, `queries/useTheses.ts`, `queries/usePortfolio.ts`
* **Dependencies**: WP-2 DTOs, TanStack Query, Zustand.
* **AC/DoD**: Query hooks return properly typed `ViewModel` data structures.

### WP-5: Application Layout
* **Repository Paths**: `src/app`, `src/components/layout`
* **Files To Create**: `src/app/layout.tsx`, `GlobalSidebar.tsx`, `GlobalHeader.tsx`, `SearchCommandPalette.tsx`
* **Dependencies**: WP-3 Shared UI, WP-4 Hooks (Search).
* **AC/DoD**: Layout renders and responds to `⌘K`.

### WP-6: Core Workspaces
* **Repository Paths**: `src/app/(dashboard)/*`, `src/features/*`
* **Files To Create**: `page.tsx` for Portfolio, Theses, Research, Memos, Performance, Analysts, Oversight, Infrastructure.
* **Dependencies**: WP-4 Hooks, WP-3 UI, WP-5 Layout.
* **AC/DoD**: All pages successfully render data from the API / Mocks.

## 3. File Generation Matrix
| File Path | Purpose | Owner Story | Dependencies |
|---|---|---|---|
| `src/types/api.d.ts` | Base API interfaces | WP-2 | None |
| `src/api/client.ts` | Axios/fetch interceptor | WP-2 | None |
| `src/components/grid/DataTable.tsx` | AG Grid React Wrapper | WP-3 | AG Grid packages |
| `src/state/useUIStore.ts` | Zustand Sidebar/Theme state | WP-4 | Zustand |
| `src/features/theses/api/getTheses.ts` | Fetcher function | WP-4 | `src/api/client.ts` |
| `src/features/theses/hooks/useTheses.ts` | React Query Hook | WP-4 | `getTheses.ts`, `ThesisViewModel` |
| `src/features/theses/models/thesis.viewmodel.ts` | UI mapping interface | WP-4 | DTO types |
| `src/features/theses/mappers/thesis.mapper.ts` | DTO -> ViewModel logic | WP-4 | DTO & ViewModel |
| `src/app/(dashboard)/theses/page.tsx` | Next.js Page Route | WP-6 | `useTheses`, `DataTable` |

## 4. Code Generation Order
* **Wave 1: Foundation**: Scaffold Next.js, install dependencies, setup Tailwind & standard configs.
* **Wave 2: DTOs**: Write `src/types/*.d.ts` explicitly from contracts.
* **Wave 3: API Layer**: Configure `src/api/client.ts` with base URL and error interceptors.
* **Wave 4: UI Shared**: Generate `MetricCard`, `DataTable`, `EmptyState`, `PageHeader`.
* **Wave 5: ViewModels & Mappers**: Implement `DTO -> ViewModel` functions.
* **Wave 6: Query Layer**: Write `useQuery` hooks utilizing API fetchers and Mappers.
* **Wave 7: Layout**: Build Sidebar, Header, and `⌘K` palette.
* **Wave 8: Workspaces**: Build specific page routes bridging Queries to Shared UI.
* **Wave 9: Hardening & Mocks**: Implement MSW handlers for local testing, Vitest configuration.

## 5. DTO Package
```typescript
// src/types/api.d.ts
export interface PaginationRequestDTO { page: number; size: number; }
export interface PortfolioSummaryDTO { total_aum: number; daily_pnl: number; active_theses_count: number; net_exposure: number; last_updated: string; }
export interface ThesisListDTO { thesis_urn: string; ticker: string; direction: "LONG" | "SHORT"; state: string; conviction_score: number; expected_horizon_days: number; }
export interface ResearchReportDTO { id: string; ticker: string; analyst_id: string; conviction: string; summary: string; published_at: string; }
export interface DecisionMemoDTO { decision_urn: string; thesis_urn: string; intent: string; pep_signature: string; timestamp: string; }
export interface AnalystMetricDTO { analyst_id: string; role: string; trust_score: number; win_rate: number; drawdown: number; }
export interface SearchResultDTO { type: "THESIS"|"RESEARCH"|"ANALYST"|"TICKER"; id: string; label: string; route: string; }
```

## 6. ViewModel Package
### 6.1 Domain: Theses
* **DTO**: `ThesisListDTO`
* **Mapper (`src/features/theses/mappers/thesis.mapper.ts`)**: Converts `conviction_score` float to percentage string, translates state to UI Badge color.
* **ViewModel (`thesis.viewmodel.ts`)**: 
  ```typescript
  export interface ThesisViewModel { id: string; ticker: string; direction: string; statusBadgeColor: string; convictionPct: string; horizonDays: number; }
  ```
* **UI Component**: `DataTable` inside `src/app/(dashboard)/theses/page.tsx`

### 6.2 Domain: Portfolio
* **DTO**: `PortfolioSummaryDTO`
* **Mapper**: Converts float values to localized currency strings (e.g., $15,000,000).
* **ViewModel**: 
  ```typescript
  export interface PortfolioSummaryViewModel { totalAumFormatted: string; pnlFormatted: string; isPnlPositive: boolean; activeTheses: number; }
  ```
* **UI Component**: `<MetricCard>` sequence inside `src/app/(dashboard)/page.tsx`.

## 7. Query Package
* **Query Client Provider**: Wrapped globally in `src/app/layout.tsx`.
* **Hooks Example**: `useThesesList(params)`
  * *Query Key*: `['theses', params]`
  * *Cache Policy*: `staleTime: 30000` (30s). `keepPreviousData: true` for pagination.
  * *Retry Policy*: 3 retries, exponential backoff.
  * *Error Rules*: Global `onError` in `QueryClient` triggers toast. Hook returns `isError` boolean to trigger `<ErrorState>` component locally.

## 8. Component Package
### 8.1 `<DataTable>`
* **Props**: `columnDefs: ColDef[]`, `rowData: T[]`, `isLoading: boolean`, `onRowClick?: (id) => void`.
* **Composition Rules**: Must wrap `AgGridReact` inside a `div` with `ag-theme-alpine`.
### 8.2 `<MetricCard>`
* **Props**: `title: string`, `metric: string`, `deltaText?: string`, `isPositive?: boolean`.
* **Composition Rules**: Uses Tremor `<Card>` and `<Text>`, `<Metric>`.
### 8.3 `<SearchCommandPalette>`
* **Events**: `useEffect` listens for `keydown` (⌘K). Queries backend via debounced text input.
### 8.4 `<PageHeader>`
* **Props**: `title: string`, `breadcrumbs?: Array<{label: string, href?: string}>`, `children?: ReactNode`.

## 9. Test Generation Package
* **`src/test/setup.ts`**: Configures Vitest and testing-library.
* **`src/test/mocks/handlers.ts`**: MSW definitions mocking all `/api/v1/*` responses for development without backend.
* **`src/features/theses/mappers/thesis.mapper.test.ts`**: Unit test validating DTO -> ViewModel transformations.
* **`src/components/shared/MetricCard.test.tsx`**: Component test validating green/red delta colors.

## 10. Developer Execution Checklist
- [ ] 1. Initialize `npx create-next-app@latest karsa-web --typescript --tailwind --app`.
- [ ] 2. Update `next.config.js` to set `output: "export"`.
- [ ] 3. Install packages: `@tanstack/react-query`, `zustand`, `ag-grid-react`, `@tremor/react`, `lucide-react`.
- [ ] 4. Scaffold UI primitives using `npx shadcn-ui@latest init`.
- [ ] 5. Follow Code Generation Order sequentially (Waves 1-9).
- [ ] 6. Run `npm run lint` and `npm run build` to verify static compilation.

## 11. Agent Execution Checklist
* **CRITICAL INSTRUCTION**: Act strictly as a code generator.
- [ ] Do NOT propose new features, endpoints, or routes.
- [ ] Do NOT replace AG Grid, Tremor, or TanStack Query with alternative libraries.
- [ ] Do NOT skip the DTO -> Mapper -> ViewModel architectural chain.
- [ ] Do NOT use React Context for global state (Use Zustand).
- [ ] ALWAYS map routes strictly as defined in `docs/architecture/58-karsa-web-console.md`.
- [ ] ALWAYS enforce absolute path imports alias (`@/components/`, `@/features/`).

## 12. Remaining Risks
* **Mock Data Dependence**: Implementation must rely heavily on MSW handlers initially, as local deployment of the full Python/Postgres backend matrix might be computationally expensive for the frontend developer loop.

## 13. Final Verdict
**READY_TO_CODE**
