"""FastAPI application factory -- Sprint-12. Wave-1.

build_fastapi_app() constructs the Capability Engine API.
No business endpoints in Wave-1.
"""

from fastapi import FastAPI

from karsa.capability_engine.transport.http.middleware.exception_mapper import (
    register_exception_handlers,
)
from karsa.capability_engine.transport.http.router_registry import (
    register_all_routers,
)

APP_TITLE = "Capability Engine API"
APP_VERSION = "1.0.0"


def build_fastapi_app() -> FastAPI:
    """Build and configure the Capability Engine FastAPI application.

    Returns a fully configured FastAPI instance with:
    - System routers (health, ready, version)
    - Global exception handlers
    - OpenAPI at /openapi.json
    - Swagger UI at /docs
    - ReDoc at /redoc
    """
    app = FastAPI(
        title=APP_TITLE,
        version=APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    register_exception_handlers(app)
    register_all_routers(app)

    return app
