"""Router registry -- Sprint-12. Wave-1.

Centralized router registration for the Capability Engine API.
"""

from fastapi import FastAPI

from karsa.capability_engine.transport.http.routers.capability_command_router import (
    router as command_router,
)
from karsa.capability_engine.transport.http.routers.capability_query_router import (
    router as query_router,
)
from karsa.capability_engine.transport.http.routers.health_router import (
    router as health_router,
)


def register_all_routers(app: FastAPI) -> None:
    """Register all routers on the FastAPI app."""
    app.include_router(health_router)
    app.include_router(command_router)
    app.include_router(query_router)
