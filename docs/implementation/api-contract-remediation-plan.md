# API Contract Remediation Plan

**Status:** READY
**Source:** API Contract Audit Report (Production Readiness: 42/100)
**Target:** Production Candidate (80+)
**Principle:** Fix contracts, don't redesign architecture.

---

## Phase 0: Critical Fixes (Day 1)

**Goal:** Fix broken endpoints and mount missing routers.

### Task 0.1: Mount investment_workflow router

**File:** `src/karsa/app.py`
**Action:** Add investment_workflow router import and mounting.
**Impact:** `/investments/decisions` returns 404 → 200
**Effort:** 5 minutes

### Task 0.2: Standardize error response format

**Problem:** Three different error formats:
- `{message}` (ApiClient)
- `{detail}` (FastAPI HTTPException)
- `{error_code, message}` (ErrorResponse)

**Solution:** All endpoints return `ErrorResponse` envelope:
```json
{"error_code": "...", "message": "..."}
```

**Files to modify:**
- `src/karsa/app.py` — add global exception handler for HTTPException
- `src/karsa/capability_engine/transport/http/middleware/exception_mapper.py` — already correct
- All routers that use `HTTPException` directly — convert to `ErrorResponse`

**Impact:** Consistent error handling across all endpoints
**Effort:** 2 hours

### Task 0.3: Add request ID to all responses

**Solution:** Add `X-Request-ID` header to all responses via middleware.

**File:** Create `src/karsa/middleware/request_id.py`
**Impact:** Traceability for debugging
**Effort:** 1 hour

---

## Phase 1: Missing Backend Endpoints (Day 2-3)

**Goal:** Implement backend endpoints that frontend hooks expect.

### Task 1.1: CIO Dashboard backend endpoints

**Problem:** 5 CIO dashboard hooks have no backend:
- `/api/risk/traffic-light`
- `/api/decisions/today`
- `/api/decisions/{ticker}/latest`
- `/api/risk/sector-allocation`
- `/api/performance/attribution`

**Solution:** Create `src/karsa/cio_dashboard/` bounded context with:
- `api/routes.py` — 5 GET endpoints
- `application/query_service.py` — reads from existing repos
- `infrastructure/projection.py` — reads from existing projections

**Files to create:**
- `src/karsa/cio_dashboard/__init__.py`
- `src/karsa/cio_dashboard/api/__init__.py`
- `src/karsa/cio_dashboard/api/routes.py`
- `src/karsa/cio_dashboard/application/__init__.py`
- `src/karsa/cio_dashboard/application/query_service.py`

**Tests:** 20+ tests
**Effort:** 1 day

### Task 1.2: Research/Search/Workers endpoints

**Problem:** 3 frontend hooks have no backend:
- `/research/reports`
- `/search`
- `/workers/metrics`

**Solution:** Create stub endpoints that return empty results with proper DTOs.

**Files to modify:**
- `src/karsa/research/api.py` — new file
- `src/karsa/search/api.py` — new file
- `src/karsa/workers/api.py` — new file

**Tests:** 9 tests (3 per endpoint)
**Effort:** 2 hours

### Task 1.3: Fix investment_workflow router mounting

**File:** `src/karsa/app.py`
**Action:** Add investment_workflow bootstrap and router mounting.
**Impact:** `/investments/decisions` works
**Effort:** 30 minutes

---

## Phase 2: Contract Standardization (Day 4-5)

**Goal:** Standardize DTOs, pagination, and naming.

### Task 2.1: Standardize pagination contract

**Problem:** Three different pagination patterns.

**Solution:** Create standard pagination DTO:
```python
@dataclass(frozen=True)
class PaginationDTO:
    page: int
    size: int
    total_items: int
    total_pages: int
```

**Files to create:**
- `src/karsa/shared/dto/pagination.py`

**Files to modify:**
- All endpoints that return paginated data

**Effort:** 2 hours

### Task 2.2: Standardize date format

**Problem:** Mixed date formats across DTOs.

**Solution:** All dates use ISO 8601 format (`YYYY-MM-DDTHH:MM:SSZ`).

**Files to modify:**
- All DTOs that contain date fields

**Effort:** 1 hour

### Task 2.3: Standardize naming convention

**Problem:** `snake_case` in backend DTOs vs `camelCase` in frontend ViewModels.

**Solution:** Backend uses `snake_case`. Frontend mappers convert to `camelCase`.

**Files to verify:**
- All `api/endpoints/*.ts` files
- All `features/*/utils/mappers.ts` files

**Effort:** 1 hour

### Task 2.4: Fix URL prefix inconsistency

**Problem:** Some CIO hooks use `/api/...` prefix, others use bare paths.

**Solution:** All capability_engine endpoints use `/capabilities/...` prefix. All investment endpoints use `/investments/...` prefix. No `/api/` prefix.

**Files to modify:**
- `karsa-web/src/hooks/cio-dashboard/index.ts` — fix URLs

**Effort:** 30 minutes

---

## Phase 3: Type Safety & Validation (Day 6-7)

**Goal:** Add runtime validation and fix untyped hooks.

### Task 3.1: Fix intelligence hooks type safety

**Problem:** 4 hooks return untyped `any`.

**Solution:** Create typed DTOs and use them in hooks.

**Files to create:**
- `karsa-web/src/features/intelligence/types/viewmodels.ts`

**Files to modify:**
- `karsa-web/src/hooks/intelligence/index.ts` — add types

**Effort:** 2 hours

### Task 3.2: Add runtime validation

**Problem:** No runtime schema validation on API responses.

**Solution:** Add Zod schemas for critical API responses.

**Files to create:**
- `karsa-web/src/api/schemas/portfolio.ts`
- `karsa-web/src/api/schemas/allocation.ts`
- `karsa-web/src/api/schemas/capabilities.ts`

**Files to modify:**
- `karsa-web/src/api/endpoints/*.ts` — add `.parse()` calls

**Effort:** 1 day

### Task 3.3: Fix stub hooks

**Problem:** 4 hooks return hardcoded empty data.

**Solution:** Connect stubs to real API endpoints.

**Files to modify:**
- `karsa-web/src/hooks/analysts/index.ts`
- `karsa-web/src/hooks/performance/index.ts`
- `karsa-web/src/hooks/research/index.ts`
- `karsa-web/src/hooks/theses/index.ts`

**Effort:** 2 hours

---

## Phase 4: Security & Production Readiness (Day 8-9)

**Goal:** Add authentication, rate limiting, and monitoring.

### Task 4.1: Implement authentication

**Problem:** No authentication on any endpoint.

**Solution:** Add JWT authentication middleware.

**Files to create:**
- `src/karsa/middleware/auth.py`
- `karsa-web/src/api/interceptors/auth-interceptor.ts` — activate

**Effort:** 1 day

### Task 4.2: Add rate limiting

**Solution:** Add rate limiting middleware.

**Files to create:**
- `src/karsa/middleware/rate_limit.py`

**Effort:** 2 hours

### Task 4.3: Add CORS configuration

**Solution:** Configure CORS for frontend.

**Files to modify:**
- `src/karsa/app.py` — add CORS middleware

**Effort:** 30 minutes

### Task 4.4: Health check with dependency status

**Solution:** Extend `/health` to include dependency status.

**Files to modify:**
- `src/karsa/app.py` — enhance health endpoint

**Effort:** 1 hour

---

## Phase 5: Consolidation (Day 10)

**Goal:** Consolidate fetch strategies and clean up.

### Task 5.1: Consolidate fetch on ApiClient

**Problem:** Two parallel fetch strategies.

**Solution:** Migrate CIO dashboard hooks to use `ApiClient`.

**Files to modify:**
- `karsa-web/src/hooks/cio-dashboard/index.ts` — use ApiClient
- `karsa-web/src/hooks/intelligence/index.ts` — use ApiClient

**Effort:** 2 hours

### Task 5.2: Add API versioning

**Solution:** Add `/api/v1/` prefix to all endpoints.

**Files to modify:**
- All router files — add prefix
- All frontend API calls — update URLs

**Effort:** 2 hours

### Task 5.3: Final audit

**Action:** Re-run API contract audit to verify score improvement.

**Target:** 80+/100 (Production Candidate)

---

## Dependency Graph

```
Phase 0 (Critical) ─────────────────────────────┐
  │                                               │
  ▼                                               │
Phase 1 (Missing Endpoints) ────────────────┐     │
  │                                          │     │
  ▼                                          ▼     │
Phase 2 (Standardization) ──────────┐       │     │
  │                                  │       │     │
  ▼                                  ▼       ▼     │
Phase 3 (Type Safety) ────────┐    │       │     │
  │                            │    │       │     │
  ▼                            ▼    ▼       ▼     ▼
Phase 4 (Security) ──────┐   │    │       │     │
  │                       │   │    │       │     │
  ▼                       ▼   ▼    ▼       ▼     ▼
Phase 5 (Consolidation) ──────────────────────────┘
```

---

## Test Targets

| Phase | New Tests | Cumulative |
|---|---|---|
| Phase 0 | 10 | 10 |
| Phase 1 | 30 | 40 |
| Phase 2 | 15 | 55 |
| Phase 3 | 20 | 75 |
| Phase 4 | 15 | 90 |
| Phase 5 | 10 | 100 |

---

## Success Criteria

| Metric | Current | Target |
|---|---|---|
| API Coverage | 4/10 | 9/10 |
| DTO Coverage | 6/10 | 9/10 |
| Error Handling | 3/10 | 9/10 |
| Type Safety | 4/10 | 8/10 |
| Pagination | 3/10 | 8/10 |
| Versioning | 2/10 | 7/10 |
| Authentication | 0/10 | 8/10 |
| Consistency | 4/10 | 9/10 |
| **Total** | **42/100** | **80+/100** |

---

## Effort Estimate

| Phase | Duration | Priority |
|---|---|---|
| Phase 0 | 1 day | P0 — Critical |
| Phase 1 | 2 days | P0 — Critical |
| Phase 2 | 2 days | P1 — High |
| Phase 3 | 2 days | P1 — High |
| Phase 4 | 2 days | P1 — High |
| Phase 5 | 1 day | P2 — Medium |
| **Total** | **10 days** | |
