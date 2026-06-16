# Sprint-51 Implementation Readiness Plan

## 1. Executive Summary
This document serves as the implementation execution plan for the Sprint-51 Karsa Web Console. Following the frozen architecture defined in `docs/architecture/58-karsa-web-console.md`, this plan details the technical roadmap required to build the Virtual Investment Firm Operations Console. The implementation exclusively targets a `Next.js` static export application integrated against existing backend CQRS projections, introducing no new bounded contexts or autonomous engine modifications.

## 2. Governance Compliance Verification
* **DOCUMENTATION_STYLE_GUIDE.md**: Compliant. Output uses standard markdown tables, absolute links, and mandated artifact directories.
* **WORKFLOW_RULES.md**: Compliant. No architecture redesign is present; this bridges frozen architecture to implementation tickets.
* **ROADMAP.md**: Compliant. Targets the Sprint-51 Karsa Web Console milestone exactly.
* **ENGINEERING_STANDARDS.md**: Compliant. Adheres to strict typing (`TypeScript`), static analysis boundaries, and stateless static frontend deployment targets.

## 3. Architecture Compliance Report
This implementation plan strictly derives from `58-karsa-web-console.md`.
* **Excluded**: Knowledge Graph visualizer, Watchlist UX, Deep Capital Allocation explanations (Explicitly out of scope per Sprint-51 review).
* **Included**: CIO Dashboard, Next.js static architecture, API mapping, TanStack query integrations, and AG Grid configurations.
* **Result**: 100% Architecture Compliance.

## 4. Screen Inventory
1. **CIO Dashboard**: Global summary, top conviction theses, daily pipeline shifts.
2. **Portfolio Console**: Holistic capital allocation and sector exposure heatmaps.
3. **Research Workspace**: Feed of processed SEC filings and generated reports.
4. **Thesis Workspace**: Ranked table of active/invalidated theses.
5. **Thesis Detail**: Hub-and-spoke view mapping Research -> Thesis -> Decisions -> Outcomes.
6. **Investment Memos**: Read-only journal of specific trade intentions.
7. **Performance & Attribution**: Return decomposition (Selection, Beta, etc.).
8. **Analysts (Worker Console)**: Performance, Trust Scores, and Drawdown of AI analysts.
9. **Investment Oversight**: Post-mortem aggregation and governance logs.
10. **Infrastructure Health**: System worker lag and database heuristics.

## 5. Route Inventory
| Route | Component | Data Source (API) |
|---|---|---|
| `/` | `CIODashboardPage` | `/api/v1/portfolio/summary`, `/api/v1/theses/top` |
| `/portfolio` | `PortfolioPage` | `/api/v1/portfolio/exposure` |
| `/research` | `ResearchWorkspacePage` | `/api/v1/research/reports` |
| `/theses` | `ThesisWorkspacePage` | `/api/v1/theses` |
| `/theses/[id]` | `ThesisDetailPage` | `/api/v1/theses/{id}/lineage` |
| `/memos` | `InvestmentMemosPage` | `/api/v1/decisions` |
| `/performance` | `PerformanceAttributionPage`| `/api/v1/performance/attribution` |
| `/analysts` | `AnalystsPage` | `/api/v1/workers/metrics` |
| `/oversight` | `InvestmentOversightPage` | `/api/v1/governance/postmortems` |
| `/infrastructure`| `InfrastructureHealthPage`| `/api/v1/observability/health` |

## 6. Component Hierarchy
```text
RootLayout (Provides TanStack Query Client, Zustand Store)
├── GlobalHeader
│   ├── CommandPalette (⌘K)
│   ├── PipelineStatusBadge
│   └── UserProfileAvatar
├── GlobalSidebar
│   └── NavigationLinks
└── MainContentPane
    └── [Page Component]
        ├── OverviewCards (Tremor)
        ├── DataGrid (AG Grid)
        └── DetailsSidebar (shadcn/ui Sheet)
```

## 7. API Contract Matrix
| Endpoint | Method | Response Interface | Consumer |
|---|---|---|---|
| `/api/v1/search` | GET | `SearchResultDTO[]` | CommandPalette |
| `/api/v1/theses` | GET | `ThesisListDTO[]` | ThesisWorkspacePage |
| `/api/v1/theses/{id}/lineage` | GET | `ThesisLineageDTO` | ThesisDetailPage |
| `/api/v1/workers/metrics` | GET | `AnalystMetricDTO[]` | AnalystsPage |
| `/api/v1/portfolio/exposure` | GET | `ExposureHeatmapDTO` | PortfolioPage |

*(Note: API implementations are existing or read-only CQRS projections exposed by the API Gateway.)*

## 8. State Management Design
* **Server State**: `TanStack Query`. Handles 95% of state. Configured with `staleTime: 60000` (1 minute) to protect backend polling rates.
* **Client State**: `Zustand`. Stores purely cosmetic preferences (e.g., `isSidebarCollapsed`, `activeTheme`, `lastViewedThesis`).
* **URL State**: Next.js App Router query parameters (`?sort=conviction&dir=desc`). All grid sorting/filtering must reflect in the URL for shareability.

## 9. RBAC Matrix
| Role | CIO Dashboard | Analysts | Oversight | Infrastructure |
|---|---|---|---|---|
| **CIO/Operator** | Read | Read | Read | Hidden |
| **Quant / Analyst** | Read | Read | Hidden | Hidden |
| **System Admin** | Read | Read | Read | Read |

*(Note: Roles are enforced as UI visibility layers; the API gateway validates the actual JWT.)*

## 10. Folder Structure
```text
src/
├── app/
│   ├── (dashboard)/
│   │   ├── theses/
│   │   │   ├── [id]/page.tsx
│   │   │   └── page.tsx
│   │   ├── analysts/page.tsx
│   │   ├── portfolio/page.tsx
│   │   └── page.tsx
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── ui/          # shadcn/ui generic primitives
│   ├── charts/      # Tremor/Recharts abstractions
│   └── grids/       # AG Grid abstractions
├── lib/
│   ├── api/         # TanStack Query fetchers
│   └── store/       # Zustand store definitions
└── types/           # Shared TypeScript interfaces (DTOs)
```

## 11. Implementation Sequence
1. **Foundation**: Scaffold Next.js, shadcn/ui, Tailwind, and Zustand.
2. **Layout**: Implement Global Sidebar, Header, and ⌘K Palette skeleton.
3. **Data Layer**: Configure TanStack Query client and API base fetchers.
4. **Core Views**: Implement Thesis Workspace (AG Grid) and Analysts Workspace.
5. **Hub View**: Implement Thesis Detail Page (Lineage mapping).
6. **Dashboard**: Implement CIO Dashboard integrating Tremor charts.
7. **Optimization**: Finalize Next.js Static Export build configuration and Nginx Dockerfile.

## 12. Story Breakdown
* **WP-1**: Next.js App Router scaffolding + UI Library injection.
* **WP-2**: Layout Shell & Navigation Context.
* **WP-3**: `⌘K` Command Palette component integration.
* **WP-4**: Thesis Workspace (`AG Grid` integration for ranked lists).
* **WP-5**: Thesis Detail Page (Hub-and-spoke layout).
* **WP-6**: Analysts Workspace (Worker Trust Scores & Calibration metrics).
* **WP-7**: Portfolio Console (Tremor Chart integrations).
* **WP-8**: CIO Dashboard Assembly.
* **WP-9**: Static Export Pipeline & Dockerization.

## 13. Test Strategy
* **Unit Testing**: `Vitest` for Zustand store logic, date formatting, and data transformation utilities.
* **Component Testing**: `React Testing Library` for critical UI paths (Command Palette triggering, Sidebar collapsing).
* **E2E Testing**: Defers to manual operator verification for Sprint-51 home-lab constraints. Playwright to be evaluated in a later sprint.
* **Type Checking**: `tsc --noEmit` runs on all CI builds.

## 14. Production Readiness Review
* **Memory Limits**: The static output relies entirely on client browser memory. Nginx footprint is guaranteed < 15MB. AG Grid ensures DOM bloat is prevented.
* **Build Step**: Command `next build` successfully generates the `out/` directory. No Node.js runtime is required.
* **API Rate Limiting**: Client-side deduplication via TanStack Query protects the backend from infinite re-renders.

## 15. Risks
* **API Mismatch**: The UI expects perfectly aggregated `ThesisLineageDTO` models. If the backend requires multiple disjointed requests to build the Thesis Detail page, browser-side networking latency will increase.
* **AG Grid Bundle Size**: Including AG Grid may balloon the initial Javascript chunk size if code-splitting is not properly configured.

## 16. Implementation Blockers
None. The architecture relies on widely available, stable open-source libraries. If specific CQRS backend endpoints are missing, mock JSON responses will be used to unblock UI development.

## 17. Architecture Compliance Evidence
* **Requirement**: Static Export. **Evidence**: `WP-9` enforces Nginx containerization.
* **Requirement**: Thesis Ranking. **Evidence**: `WP-4` mandates AG Grid for interactive sorting.
* **Requirement**: Semantic Shift. **Evidence**: `Route Inventory` uses `/analysts`, `/oversight`, `/memos`.

## 18. Roadmap Compliance Assessment
Sprint-51 is accurately scoped to the "Web Console Implementation" phase. No drift into Sprint-52 (Watchlists/Knowledge Graphs) exists in the story breakdown.

## 19. Engineering Standards Compliance Assessment
* **Language**: TypeScript strictly enforced.
* **Dependency Constraint**: Approved libraries only (React, Next, TanStack, Zustand, Tremor, AG Grid).
* **Deployment**: Fits the existing `docker-compose.yml` Lenovo Tiny constraints via lightweight Nginx static hosting.

## 20. Final Verdict
**IMPLEMENTATION_READY**
