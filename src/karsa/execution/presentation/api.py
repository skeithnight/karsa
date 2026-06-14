from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from karsa.execution.application.services import (
    OrderPEPService, OrderRoutingService, FillService, ExecutionStateProjectionService
)
from karsa.execution.domain.exceptions import (
    SignatureVerificationError, PolicyLimitExceededError, BrokerRoutingError,
    ExecutionNotFoundError
)

router = APIRouter(prefix="/api/v1/execution/orders", tags=["execution"])


# ----------------- Request / Response Models -----------------

class StageOrderRequest(BaseModel):
    execution_id: str
    correlation_id: str
    causation_id: str
    symbol: str
    quantity: float
    direction: str
    order_type: str = "MARKET"
    price: Optional[float] = None
    cio_signature: str
    gov_exception_id: Optional[str] = None
    gov_exception_signature: Optional[str] = None


class StageOrderResponse(BaseModel):
    execution_id: str
    pep_status: str
    pep_token_signature: Optional[str] = None
    message: str


class OrderStateResponse(BaseModel):
    execution_id: str
    state: str


class RouteOrderResponse(BaseModel):
    route_id: str
    execution_id: str
    status: str


class RecordFillRequest(BaseModel):
    route_id: str
    filled_quantity: float
    filled_price: float
    commission: float
    slippage: float
    correlation_id: Optional[str] = None


class RecordFillResponse(BaseModel):
    fill_id: str
    route_id: str
    status: str


# ----------------- Dependency Injection Stubs -----------------

def get_pep_service() -> OrderPEPService:
    raise NotImplementedError("Dependency must be overridden in app bootstrap")


def get_routing_service() -> OrderRoutingService:
    raise NotImplementedError("Dependency must be overridden in app bootstrap")


def get_fill_service() -> FillService:
    raise NotImplementedError("Dependency must be overridden in app bootstrap")


def get_projection_service() -> ExecutionStateProjectionService:
    raise NotImplementedError("Dependency must be overridden in app bootstrap")


# ----------------- Endpoint Definitions -----------------

@router.post("/stage", response_model=StageOrderResponse, status_code=201)
def stage_order(
    req: StageOrderRequest,
    pep_service: OrderPEPService = Depends(get_pep_service)
) -> StageOrderResponse:
    """Stages an order and runs the PEP dual-signature validation."""
    try:
        token = pep_service.stage_and_validate(
            execution_id=req.execution_id,
            correlation_id=req.correlation_id,
            causation_id=req.causation_id,
            symbol=req.symbol,
            quantity=req.quantity,
            direction=req.direction,
            order_type=req.order_type,
            price=req.price,
            cio_signature=req.cio_signature,
            gov_exception_id=req.gov_exception_id,
            gov_exception_signature=req.gov_exception_signature,
        )
        return StageOrderResponse(
            execution_id=req.execution_id,
            pep_status="PEP_VALIDATED",
            pep_token_signature=token,
            message="Order staged and validated successfully."
        )
    except (SignatureVerificationError, PolicyLimitExceededError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.post("/{execution_id}/route", response_model=RouteOrderResponse)
def route_order(
    execution_id: str,
    routing_service: OrderRoutingService = Depends(get_routing_service)
) -> RouteOrderResponse:
    """Routes a validated staged order to the broker venue."""
    try:
        route_id = routing_service.route_order(execution_id)
        return RouteOrderResponse(
            route_id=route_id,
            execution_id=execution_id,
            status="ROUTED"
        )
    except ExecutionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BrokerRoutingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.post("/fill", response_model=RecordFillResponse, status_code=201)
def record_fill(
    req: RecordFillRequest,
    fill_service: FillService = Depends(get_fill_service)
) -> RecordFillResponse:
    """Logs broker fill execution records to the ledger."""
    try:
        fill_id = fill_service.record_fill(
            route_id=req.route_id,
            filled_quantity=req.filled_quantity,
            filled_price=req.filled_price,
            commission=req.commission,
            slippage=req.slippage,
            correlation_id=req.correlation_id or ""
        )
        return RecordFillResponse(
            fill_id=fill_id,
            route_id=req.route_id,
            status="FILLED"
        )
    except ExecutionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/{execution_id}/state", response_model=OrderStateResponse)
def get_order_state(
    execution_id: str,
    projection_service: ExecutionStateProjectionService = Depends(get_projection_service)
) -> OrderStateResponse:
    """Queries the projected state of the staged order."""
    try:
        state = projection_service.get_execution_state(execution_id)
        return OrderStateResponse(
            execution_id=execution_id,
            state=state.value
        )
    except ExecutionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
