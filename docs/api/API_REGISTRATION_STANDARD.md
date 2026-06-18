# API Registration Standard

## Context
Karsa utilizes a monolithic FastAPI backend container (`karsa-api`). To prevent router fragmentation and lifecycle complexity, all domain APIs must strictly conform to a centralized dependency injection and registration paradigm.

## Current FastAPI Registration Patterns
*   **Location**: `src/karsa/app.py`.
*   **Dependency Injection**: Driven via `ApplicationContainer` and the FastAPI `lifespan` function overriding `app.dependency_overrides`.
*   **Router Mounting**: Standardized at the bottom of the `app.py` script (`app.include_router()`).

## Required Standard
All new validation platform contexts MUST implement a standalone `api.py` (or `presentation/api.py`) defining:
1.  A standalone `APIRouter` with an explicitly tagged prefix (e.g., `prefix="/api/v1/trust", tags=["trust"]`).
2.  Dependency fetcher functions (e.g., `def get_trust_service() -> TrustService:`).

### Context Specific Registrations
*   **Attribution**: `prefix="/api/v1/attribution"`. Re-wire existing commands into `app.py`.
*   **Review**: `prefix="/api/v1/review"`. Grouped under `tags=["review"]`.
*   **Trust**: `prefix="/api/v1/trust"`. Grouped under `tags=["trust"]`.
*   **Prediction Center**: `prefix="/api/v1/prediction-center"`. Acts purely as a BFF returning aggregated Context DTOs.
*   **Firm Health**: `prefix="/api/v1/firm-health"`. Aggregates TSDB data exclusively for executive dashboards.

## Acceptance Criteria
*   Zero standalone uvicorn runs. All traffic routes through `karsa-api` entrypoint.
*   Domain isolation is maintained at the router level.
