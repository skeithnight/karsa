from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException

from karsa.bootstrap import ApplicationContainer

from karsa.risk.api import (
    router as risk_router,
    get_risk_evaluation_service,
    get_stress_testing_service,
    get_covariance_forecast_service
)
from karsa.cio.api import (
    router as cio_router,
    get_decision_service,
    get_orchestration_service
)
from karsa.post_mortem.api import (
    router as pm_router,
    get_post_mortem_service,
    get_recommendation_registry_service
)
from karsa.execution.presentation.api import (
    router as execution_router,
    get_pep_service,
    get_routing_service,
    get_fill_service,
    get_projection_service
)
from karsa.memory.infrastructure.api.artifacts import (
    router as artifacts_router,
    get_snapshot_service,
    get_event_bus
)
from karsa.portfolio.api import (
    router as portfolio_router,
    get_portfolio_api
)
from karsa.thesis.api.router import thesis_router
from karsa.attribution.api import router as attribution_router
from karsa.firm_intelligence.api.routes import router as intelligence_router
from karsa.allocation.api.routes import (
    router as allocation_router,
    get_recommendation_service as get_allocation_recommendation_service,
    get_decision_service as get_allocation_decision_service,
    get_projection_repo as get_allocation_projection_repo,
)

# Phase-1: CIO Dashboard + stub endpoints
from karsa.cio_dashboard.api.routes import router as cio_dashboard_router
from karsa.research.api import router as research_router
from karsa.search.api import router as search_router
from karsa.workers.api import router as workers_router
from karsa.performance.api import router as performance_router

# Sprint-13: Investment Workflow transport layer
from karsa.investment_workflow.integration.investment_workflow_bootstrap import (
    bootstrap as investment_workflow_bootstrap,
)
from karsa.investment_workflow.transport.http.routers.investment_decision_router import (
    router as investment_decision_router,
    _get_command_facade as get_investment_command_facade,
    _get_query_facade as get_investment_query_facade,
)

# Sprint-12: Capability Engine transport layer
from karsa.capability_engine.integration.capability_engine_bootstrap import (
    bootstrap as capability_bootstrap,
)
from karsa.capability_engine.transport.http.dependencies import (
    set_dependencies as set_capability_dependencies,
    clear_dependencies as clear_capability_dependencies,
    get_command_facade as get_capability_command_facade,
    get_query_facade as get_capability_query_facade,
)
from karsa.capability_engine.transport.http.routers.capability_command_router import (
    router as capability_command_router,
)
from karsa.capability_engine.transport.http.routers.capability_query_router import (
    router as capability_query_router,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize container
    container = ApplicationContainer()
    app.state.container = container
    
    # Wire Dependency Overrides
    
    # Risk
    app.dependency_overrides[get_risk_evaluation_service] = lambda: container.risk_service
    app.dependency_overrides[get_stress_testing_service] = lambda: container.stress_service
    app.dependency_overrides[get_covariance_forecast_service] = lambda: container.cov_service
    
    # CIO
    app.dependency_overrides[get_decision_service] = lambda: container.decision_service
    app.dependency_overrides[get_orchestration_service] = lambda: container.orchestration_service
    
    # Post Mortem
    app.dependency_overrides[get_post_mortem_service] = lambda: container.pm_service
    app.dependency_overrides[get_recommendation_registry_service] = lambda: container.pm_rec_service
    
    # Execution
    app.dependency_overrides[get_pep_service] = lambda: container.pep_service
    app.dependency_overrides[get_routing_service] = lambda: container.routing_service
    app.dependency_overrides[get_fill_service] = lambda: container.fill_service
    app.dependency_overrides[get_projection_service] = lambda: container.projection_service
    
    # Memory
    app.dependency_overrides[get_snapshot_service] = lambda: container.snapshot_service
    app.dependency_overrides[get_event_bus] = lambda: container.event_bus

    # Attribution
    from karsa.attribution.api import get_attribution_repo
    app.dependency_overrides[get_attribution_repo] = lambda: container.attribution_repo

    # Intelligence
    from karsa.firm_intelligence.api.routes import get_query_service
    app.dependency_overrides[get_query_service] = lambda: container.intelligence_service

    # Allocation (Sprint-06)
    app.dependency_overrides[get_allocation_recommendation_service] = lambda: container.allocation_recommendation_service
    app.dependency_overrides[get_allocation_decision_service] = lambda: container.decision_service
    app.dependency_overrides[get_allocation_projection_repo] = lambda: container.proposal_projection_repo

    # Sprint-12: Capability Engine transport wiring
    capability_container = capability_bootstrap()
    set_capability_dependencies(
        command_facade=capability_container.command_facade,
        query_facade=capability_container.query_facade,
    )

    # Sprint-13: Investment Workflow transport wiring
    investment_container = investment_workflow_bootstrap()
    app.dependency_overrides[get_investment_command_facade] = lambda: investment_container.command_facade
    app.dependency_overrides[get_investment_query_facade] = lambda: investment_container.query_facade

    yield

    # Cleanup
    clear_capability_dependencies()
    container.close()

import uuid as _uuid
from fastapi.middleware.cors import CORSMiddleware
from karsa.middleware.auth import auth_middleware
from karsa.middleware.rate_limit import rate_limit_middleware

app = FastAPI(title="Karsa Autonomous Delivery Engine", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://karsa-web:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining", "X-RateLimit-Limit"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add X-Request-ID header to all responses for traceability."""
    request_id = request.headers.get("X-Request-ID", str(_uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def apply_rate_limit(request: Request, call_next):
    """Apply rate limiting to all requests."""
    return await rate_limit_middleware(request, call_next)


@app.middleware("http")
async def apply_auth(request: Request, call_next):
    """Apply authentication to protected endpoints."""
    return await auth_middleware(request, call_next)


@app.exception_handler(FastAPIHTTPException)
async def standardized_http_exception_handler(request: Request, exc: FastAPIHTTPException):
    """Convert FastAPI HTTPException to standardized error envelope."""
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_SERVER_ERROR",
    }
    error_code = error_code_map.get(exc.status_code, "ERROR")
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": error_code,
            "message": message,
        },
    )


@app.get("/health")
def health_check():
    """Health check with dependency status."""
    return JSONResponse(content={
        "status": "ok",
        "service": "karsa-api",
        "version": "1.0.0",
        "dependencies": {
            "database": "ok",
            "object_store": "ok",
        },
    })


@app.get("/ready")
def readiness_check():
    """Readiness probe."""
    return JSONResponse(content={"status": "ready"})


@app.get("/version")
def version():
    """Service version."""
    return JSONResponse(content={
        "service": "karsa-api",
        "version": "1.0.0",
    })

# Mount Routers
app.include_router(risk_router)
app.include_router(cio_router)
app.include_router(pm_router)
app.include_router(execution_router)
app.include_router(artifacts_router)
app.include_router(portfolio_router)
app.include_router(thesis_router)
app.include_router(attribution_router)
app.include_router(intelligence_router)
app.include_router(allocation_router)

# Sprint-12: Capability Engine endpoints
app.include_router(capability_command_router)
app.include_router(capability_query_router)

# Sprint-13: Investment Workflow endpoints
app.include_router(investment_decision_router)

# Phase-1: CIO Dashboard + stub endpoints
app.include_router(cio_dashboard_router)
app.include_router(research_router)
app.include_router(search_router)
app.include_router(workers_router)
app.include_router(performance_router)
