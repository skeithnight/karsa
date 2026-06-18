from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse

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

    yield
    
    # Cleanup
    container.close()

app = FastAPI(title="Karsa Autonomous Delivery Engine", lifespan=lifespan)

@app.get("/health")
def health_check():
    return JSONResponse(content={"status": "ok"})

# Mount Routers
app.include_router(risk_router)
app.include_router(cio_router)
app.include_router(pm_router)
app.include_router(execution_router)
app.include_router(artifacts_router)
app.include_router(portfolio_router)
