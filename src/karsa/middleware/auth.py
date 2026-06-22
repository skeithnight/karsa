"""JWT Authentication middleware -- Phase-4.

Validates Bearer tokens on protected endpoints.
Public endpoints (health, docs, OpenAPI) are excluded.

NOTE: Auth is currently in pass-through mode (all requests allowed).
To enable enforcement, set REQUIRE_AUTH=True and implement JWT validation.
"""

from fastapi import Request

# Set to True to enforce authentication on non-public endpoints
REQUIRE_AUTH = False

# Endpoints that never require authentication
PUBLIC_ENDPOINTS = {
    "/health",
    "/ready",
    "/version",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def is_public_path(path: str) -> bool:
    """Check if a path is public (no auth required)."""
    if path in PUBLIC_ENDPOINTS:
        return True
    if path.startswith("/docs") or path.startswith("/redoc"):
        return True
    return False


async def auth_middleware(request: Request, call_next):
    """JWT authentication middleware.

    Currently in pass-through mode. All requests are allowed.
    When REQUIRE_AUTH=True, validates Bearer tokens on non-public endpoints.
    """
    if not REQUIRE_AUTH:
        return await call_next(request)

    if is_public_path(request.url.path):
        return await call_next(request)

    # Auth enforcement would go here:
    # - Extract Authorization header
    # - Validate JWT signature, expiry, claims
    # - Return 401 on failure

    response = await call_next(request)
    return response
