"""Health router -- Sprint-12. Wave-1.

System endpoints: /health, /ready, /version.
No business logic.
"""

from fastapi import APIRouter

router = APIRouter(tags=["System"])


@router.get("/health")
def health_check() -> dict:
    """Liveness probe."""
    return {"status": "healthy"}


@router.get("/ready")
def readiness_check() -> dict:
    """Readiness probe."""
    return {"status": "ready"}


@router.get("/version")
def version() -> dict:
    """Service version."""
    return {"service": "capability-engine", "version": "1.0.0"}
