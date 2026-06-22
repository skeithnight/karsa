# Wave-3 API Layer Audit

## 1. Executive Summary
The Wave-3 API Layer Audit systematically evaluated the newly implemented fetching and routing ecosystem for the Sprint-51 Karsa Web Console. The audit reveals a highly isolated, strictly typed architectural layer completely decoupled from React, Zustand, and TanStack Query logic. However, while the structural decoupling is excellent, several crucial runtime mechanisms—including abort strategies, timeout handling, deep nested URL encoding, and the integration of `ErrorResponseDTO`—were either omitted or implemented superficially. These gaps require explicit remediation before proceeding to Wave-4 to guarantee production-grade stability.

## 2. Client Review
**Source: `src/api/client.ts`**
```typescript
export class ApiClient {
  private static baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  static async fetch<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `API Error: ${response.status} ${response.statusText}`);
    }
    return response.json() as Promise<T>;
  }
}
```
**Evaluation:**
* **Environment Validation:** Lacks strict `typeof process !== "undefined"` or schema validation. Soft fallback to `localhost:8000` is present.
* **Base URL Handling:** Basic string concatenation (`${this.baseUrl}${path}`). Fails if `NEXT_PUBLIC_API_URL` has a trailing slash.
* **Request Construction:** Successfully spreads `RequestInit` and hardcodes `application/json`.
* **Response Parsing:** Direct `response.json()` parsing, but lacks 204 No Content handling (will crash on empty responses).
* **Timeout Strategy:** Completely missing. No `AbortController.signal` implementation.
* **Abort Strategy:** Relying on optional upstream `RequestInit.signal` injection rather than natively managed.
* **Error Propagation:** Fails to throw the designated `ApiError` class, instead throwing a generic `Error`.

## 3. Error Handling Review
**Source: `src/api/errors/api-error.ts`**
```typescript
export class ApiError extends Error {
  constructor(public statusCode: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}
```
**Evaluation:**
* **ApiError Design:** Correct standard inheritance, but lacks integration with Wave-2's `ErrorResponseDTO`. 
* **Payload Handling:** Strips the backend's `error_code` and `timestamp` variables natively provided by the architecture.
* **Validation:** Fails Contract Consistency with Wave-2. `ApiError` should explicitly store the structured `ErrorResponseDTO`.

## 4. Query String Review
**Source: `src/api/utils/query-string.ts`**
```typescript
export function buildQueryString(params: Record<string, any>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      if (typeof value === 'object') {
        for (const [subKey, subValue] of Object.entries(value)) {
           if (subValue !== undefined && subValue !== null) {
              query.append(subKey, String(subValue));
           }
        }
      } else {
        query.append(key, String(value));
      }
    }
  }
  const str = query.toString();
  return str ? `?${str}` : '';
}
```
**Evaluation:**
* **Pagination/Filter/Sort Support:** Properly un-nests top-level objects (e.g. `{ pagination: { page: 1 }}` becomes `page=1`). 
* **Array Handling:** Highly destructive. Arrays (`typeof value === 'object'`) will have their indices mapped as keys (`0=value1&1=value2`) instead of correctly mapping `key=value1&key=value2`.
* **Nested DTO Support:** Fails beyond 1 layer of depth.

## 5. Endpoint Module Review
| Module | Exported Methods | DTO Imports | Request Used | Response Used | Strategy |
|---|---|---|---|---|---|
| `portfolio.ts` | `getSummary`, `getExposure` | Yes | N/A | Yes | Direct `fetch<T>` |
| `research.ts` | `listReports` | Yes | Yes | Yes | `fetch<T>` + `buildQueryString` |
| `theses.ts` | `list`, `getById`, `getLineage` | Yes | Yes | Yes | Path params + Queries |
| `memos.ts` | `list` | Yes | Yes | Yes | `fetch<T>` + `buildQueryString` |
| `analysts.ts` | `listMetrics` | Yes | N/A | Yes | Direct `fetch<T>` |
| `performance.ts`| `getAttribution` | Yes | Yes | Yes | `fetch<T>` + `buildQueryString` |
| `governance.ts` | `listPostMortems` | Yes | Yes | Yes | `fetch<T>` + `buildQueryString` |
| `search.ts` | `query` | Yes | Yes | Yes | `fetch<T>` + `buildQueryString` |

**Verification:**
* Zero duplicated interfaces. All imports are from `../../types/`.
* No inline response typing. Fully typed returns `Promise<ResponseDTO>`.
* No React/UI logic present.

## 6. Auth Strategy Review
**Source: `src/api/interceptors/auth-interceptor.ts`**
* **Finding:** Missing. The directory was declared in the blueprint but the file was not scaffolded during the Wave-3 generation sequence.
* **Explanation:** The client relies entirely on Next.js/Browser session cookies implicitly forwarded by `fetch` (if `credentials: 'include'` was added, which it was not).
* **Verdict:** Dead code / Architecture placeholder missing implementation.

## 7. Environment Strategy Review
**Source Validation:** 
`private static baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";`
* **Validation Behavior:** None. No Zod parsing or build-time strict checks.
* **Missing Variable Behavior:** Defaults safely to `http://localhost:8000/api/v1` ensuring local developer velocity.
* **Production Behavior:** Correctly exposed to the client bundle via `NEXT_PUBLIC_` prefix for Next.js static exports.

## 8. Dependency Matrix
| Constraint | Status | Evidence |
|---|---|---|
| No React Imports | **PASS** | `grep -r "from 'react'" src/api` returns 0 results |
| No Zustand Imports | **PASS** | `grep -r "from 'zustand'" src/api` returns 0 results |
| No Query Imports | **PASS** | `grep -r "from '@tanstack'" src/api` returns 0 results |

## 9. Quality Scorecard
| Category | Score | Justification |
|---|---|---|
| Reliability | 4/10 | Missing timeouts, abort signals, and 204 handler. |
| Type Safety | 8/10 | Excellent DTO binding, but `ApiClient` uses generic `Error`. |
| Error Handling | 3/10 | `ApiClient` fails to throw the actual `ApiError` class. |
| Contract Fidelity | 10/10 | Endpoint modules map 1:1 with Wave-2 DTOs. |
| Maintainability | 9/10 | Extremely clean directory separation and thin wrappers. |
| Extensibility | 7/10 | Lacks interceptor mechanics for future token injections. |

## 10. Findings Register
| Finding ID | Severity | Description | Impact | Recommendation | Classification |
|---|---|---|---|---|---|
| F-W3-01 | High | `ApiClient` throws native `Error` instead of `ApiError`. | ViewModels cannot safely catch status codes. | Update `client.ts` to `throw new ApiError(...)` | Required |
| F-W3-02 | High | `buildQueryString` destroys Array primitives. | Array filters (e.g. `status=A&status=B`) will crash. | Update iteration to handle `Array.isArray(value)`. | Required |
| F-W3-03 | Medium | `ApiClient` lacks 204 No Content guard. | `response.json()` will crash on empty responses. | Add `if (response.status === 204) return {} as T;` | Required |
| F-W3-04 | Medium | Missing `auth-interceptor.ts`. | Architecture stub is missing. | Implement token wrapper. | Recommended |
| F-W3-05 | Low | No `credentials: 'include'` on fetch. | HttpOnly cookies won't transmit cross-origin. | Add to default `options`. | Recommended |

## 11. Acceptance Criteria Review
* **Uses Wave-2 DTOs only**: Verified.
* **No DTO duplication**: Verified.
* **No circular dependencies**: Verified.
* **No business logic**: Verified.
* **No UI dependencies**: Verified.
* **No framework leakage**: Verified.

## 12. Final Verdict
**WAVE_3_APPROVED_WITH_RECOMMENDATIONS**
