import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cryptography.hazmat.primitives.asymmetric import ed25519
from karsa.execution.domain.exceptions import (
    SignatureVerificationError, PolicyLimitExceededError, BrokerRoutingError,
    DatabaseImmutabilityError, ExecutionNotFoundError
)
from karsa.execution.domain.models import (
    ExecutionRequest, RoutingRecord, FillRecord, PEPValidationStatus, RouteStatus,
    ExecutionLifecycleState, generate_urn, validate_urn
)
from karsa.execution.domain.security import (
    generate_key_pair, sign_payload, verify_payload_signature
)
from karsa.execution.domain.events import (
    OrderStagedEvent, OrderValidatedEvent, OrderRoutedEvent, OrderFilledEvent,
    OrderRejectedEvent
)
from karsa.execution.application.ports import (
    DecisionAuthorizationPort, GovernanceAuthorizationPort
)
from karsa.execution.application.services import (
    OrderPEPService, OrderRoutingService, FillService, ExecutionStateProjectionService
)
from karsa.execution.infrastructure.repositories import (
    InMemoryExecutionRequestRepository, InMemoryRoutingRecordRepository,
    InMemoryFillRecordRepository, FileExecutionRequestRepository,
    FileRoutingRecordRepository, FileFillRecordRepository
)
from karsa.execution.infrastructure.adapters.ib_adapter import InteractiveBrokersAdapter
from karsa.execution.presentation.api import (
    router, get_pep_service, get_routing_service, get_fill_service, get_projection_service
)


# ----------------- Mock Ports Implementations -----------------

class MockDecisionAuthorizationAdapter(DecisionAuthorizationPort):
    def __init__(self, cio_public_key: ed25519.Ed25519PublicKey) -> None:
        self.cio_public_key = cio_public_key

    def verify_decision_signature(self, decision_id: str, signature: str, order_details: Dict[str, Any]) -> bool:
        # Reconstruct signature payload matching tests: decision_id + symbol + quantity
        payload = f"{decision_id}|{order_details['symbol']}|{order_details['quantity']}"
        return verify_payload_signature(self.cio_public_key, payload, signature)


class MockGovernanceAuthorizationAdapter(GovernanceAuthorizationPort):
    def __init__(self, gov_public_key: ed25519.Ed25519PublicKey, limit_amount: float = 10000.0) -> None:
        self.gov_public_key = gov_public_key
        self.limit_amount = limit_amount

    def check_policy_limits(self, order_details: Dict[str, Any]) -> bool:
        # Mock policy limit: if quantity * price > limit_amount, return False (exceeded)
        price = order_details.get("price") or 1.0
        return (order_details["quantity"] * price) <= self.limit_amount

    def verify_governance_exception(self, exception_id: str, signature: str, order_details: Dict[str, Any]) -> bool:
        # Reconstruct signature payload: exception_id + symbol
        payload = f"{exception_id}|{order_details['symbol']}"
        return verify_payload_signature(self.gov_public_key, payload, signature)


# ----------------- Test Fixtures -----------------

@pytest.fixture
def keys() -> Dict[str, Any]:
    pep_priv, pep_pub = generate_key_pair()
    cio_priv, cio_pub = generate_key_pair()
    gov_priv, gov_pub = generate_key_pair()
    return {
        "pep_priv": pep_priv, "pep_pub": pep_pub,
        "cio_priv": cio_priv, "cio_pub": cio_pub,
        "gov_priv": gov_priv, "gov_pub": gov_pub
    }


@pytest.fixture
def mock_ports(keys) -> Tuple:
    dec_port = MockDecisionAuthorizationAdapter(keys["cio_pub"])
    gov_port = MockGovernanceAuthorizationAdapter(keys["gov_pub"])
    return dec_port, gov_port


# ----------------- Unit & State Transition Tests -----------------

def test_urn_validations() -> None:
    exec_id = generate_urn("record")
    validate_urn(exec_id, "record")

    with pytest.raises(ValueError):
        validate_urn("urn:karsa:execution:invalid:123", "record")

    with pytest.raises(ValueError):
        validate_urn("urn:karsa:execution:record:", "record")


def test_immutable_ledger_record_creation() -> None:
    exec_id = generate_urn("record")
    dec_id = generate_urn("decision", context="cio")
    
    # Valid Request
    req = ExecutionRequest(
        execution_id=exec_id,
        correlation_id=dec_id,
        causation_id=dec_id,
        symbol="urn:karsa:asset:ticker:nvda",
        quantity=100.0,
        direction="BUY",
        order_type="MARKET",
        price=None,
        cio_signature="cio_sig"
    )
    assert req.execution_id == exec_id
    assert req.quantity == 100.0

    # Test domain immutability
    from dataclasses import FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        req.quantity = 200.0  # type: ignore


def test_lifecycle_projection_flow() -> None:
    req_repo = InMemoryExecutionRequestRepository()
    routing_repo = InMemoryRoutingRecordRepository()
    fill_repo = InMemoryFillRecordRepository()
    projection_service = ExecutionStateProjectionService(req_repo, routing_repo, fill_repo)

    exec_id = generate_urn("record")
    dec_id = generate_urn("decision", context="cio")

    # 0. Not Found
    with pytest.raises(ExecutionNotFoundError):
        projection_service.get_execution_state(exec_id)

    # 1. Staged / Pending PEP Validation
    req = ExecutionRequest(
        execution_id=exec_id,
        correlation_id=dec_id,
        causation_id=dec_id,
        symbol="urn:karsa:asset:ticker:nvda",
        quantity=50.0,
        direction="BUY",
        order_type="MARKET",
        price=None,
        cio_signature="cio_sig",
        pep_status=PEPValidationStatus.STAGED
    )
    req_repo.append(req)
    assert projection_service.get_execution_state(exec_id) == ExecutionLifecycleState.STAGED

    # 2. PEP Rejections
    req_repo._data.clear()
    req = ExecutionRequest(
        execution_id=exec_id,
        correlation_id=dec_id,
        causation_id=dec_id,
        symbol="urn:karsa:asset:ticker:nvda",
        quantity=50.0,
        direction="BUY",
        order_type="MARKET",
        price=None,
        cio_signature="cio_sig",
        pep_status=PEPValidationStatus.REJECTED,
        rejection_reason="Signature failed"
    )
    req_repo.append(req)
    assert projection_service.get_execution_state(exec_id) == ExecutionLifecycleState.REJECTED

    # 3. PEP Validated
    req_repo._data.clear()
    req = ExecutionRequest(
        execution_id=exec_id,
        correlation_id=dec_id,
        causation_id=dec_id,
        symbol="urn:karsa:asset:ticker:nvda",
        quantity=50.0,
        direction="BUY",
        order_type="MARKET",
        price=None,
        cio_signature="cio_sig",
        pep_status=PEPValidationStatus.PEP_VALIDATED
    )
    req_repo.append(req)
    assert projection_service.get_execution_state(exec_id) == ExecutionLifecycleState.PEP_VALIDATED

    # 4. Routed
    route_id = generate_urn("route")
    route = RoutingRecord(
        route_id=route_id,
        execution_id=exec_id,
        broker_id="ib",
        broker_order_ref="ib_ref_1",
        route_status=RouteStatus.SENT
    )
    routing_repo.append(route)
    assert projection_service.get_execution_state(exec_id) == ExecutionLifecycleState.ROUTED

    # 5. Filled
    fill_id = generate_urn("fill")
    fill = FillRecord(
        fill_id=fill_id,
        route_id=route_id,
        filled_quantity=50.0,
        filled_price=120.0,
        commission=1.5,
        slippage=0.01
    )
    fill_repo.append(fill)
    assert projection_service.get_execution_state(exec_id) == ExecutionLifecycleState.FILLED


# ----------------- Authorization Validation & PEP Tests -----------------

def test_pep_validates_cio_signature(keys, mock_ports) -> None:
    dec_port, gov_port = mock_ports
    req_repo = InMemoryExecutionRequestRepository()
    pep_service = OrderPEPService(req_repo, dec_port, gov_port, keys["pep_priv"])

    exec_id = generate_urn("record")
    dec_id = generate_urn("decision", context="cio")
    symbol = "urn:karsa:asset:ticker:nvda"
    quantity = 10.0

    # Create valid signature
    payload = f"{dec_id}|{symbol}|{quantity}"
    valid_signature = sign_payload(keys["cio_priv"], payload)

    # 1. Invalid signature must fail
    with pytest.raises(SignatureVerificationError):
        pep_service.stage_and_validate(
            execution_id=exec_id,
            correlation_id=dec_id,
            causation_id=dec_id,
            symbol=symbol,
            quantity=quantity,
            direction="BUY",
            order_type="MARKET",
            price=None,
            cio_signature="invalid_signature"
        )
    assert req_repo.find_by_id(exec_id).pep_status == PEPValidationStatus.REJECTED # type: ignore

    # 2. Valid signature must pass within default limits
    req_repo._data.clear()
    token = pep_service.stage_and_validate(
        execution_id=exec_id,
        correlation_id=dec_id,
        causation_id=dec_id,
        symbol=symbol,
        quantity=quantity,
        direction="BUY",
        order_type="MARKET",
        price=100.0, # Total $1000, within default $10000
        cio_signature=valid_signature
    )
    assert token is not None
    assert req_repo.find_by_id(exec_id).pep_status == PEPValidationStatus.PEP_VALIDATED # type: ignore


def test_pep_governance_limit_exception(keys, mock_ports) -> None:
    dec_port, gov_port = mock_ports
    req_repo = InMemoryExecutionRequestRepository()
    pep_service = OrderPEPService(req_repo, dec_port, gov_port, keys["pep_priv"])

    exec_id = generate_urn("record")
    dec_id = generate_urn("decision", context="cio")
    exception_id = generate_urn("exception", context="governance")
    symbol = "urn:karsa:asset:ticker:nvda"
    quantity = 150.0  # At price 100.0 = total $15000, exceeding default $10000 limit

    # Valid CIO Decision signature
    cio_payload = f"{dec_id}|{symbol}|{quantity}"
    cio_signature = sign_payload(keys["cio_priv"], cio_payload)

    # 1. Exceeds limits without Exception details must fail
    exec_id_1 = generate_urn("record")
    with pytest.raises(PolicyLimitExceededError):
        pep_service.stage_and_validate(
            execution_id=exec_id_1,
            correlation_id=dec_id,
            causation_id=dec_id,
            symbol=symbol,
            quantity=quantity,
            direction="BUY",
            order_type="MARKET",
            price=100.0,
            cio_signature=cio_signature
        )

    # 2. Exceeds limits with invalid Exception signature must fail
    exec_id_2 = generate_urn("record")
    with pytest.raises(SignatureVerificationError):
        pep_service.stage_and_validate(
            execution_id=exec_id_2,
            correlation_id=dec_id,
            causation_id=dec_id,
            symbol=symbol,
            quantity=quantity,
            direction="BUY",
            order_type="MARKET",
            price=100.0,
            cio_signature=cio_signature,
            gov_exception_id=exception_id,
            gov_exception_signature="invalid_exception_sig"
        )

    # 3. Exceeds limits with valid Exception signature must pass
    exec_id_3 = generate_urn("record")
    exception_payload = f"{exception_id}|{symbol}"
    exception_signature = sign_payload(keys["gov_priv"], exception_payload)

    token = pep_service.stage_and_validate(
        execution_id=exec_id_3,
        correlation_id=dec_id,
        causation_id=dec_id,
        symbol=symbol,
        quantity=quantity,
        direction="BUY",
        order_type="MARKET",
        price=100.0,
        cio_signature=cio_signature,
        gov_exception_id=exception_id,
        gov_exception_signature=exception_signature
    )
    assert token is not None
    assert req_repo.find_by_id(exec_id_3).pep_status == PEPValidationStatus.PEP_VALIDATED # type: ignore


# ----------------- Anti-Bypass Validation Tests -----------------

def test_anti_bypass_broker_adapter(keys) -> None:
    adapter = InteractiveBrokersAdapter(keys["pep_pub"])
    exec_id = generate_urn("record")

    # 1. Route order without PEP token signature must fail
    with pytest.raises(SignatureVerificationError, match="Outbound order missing PEP transaction token"):
        adapter.route_order(
            execution_id=exec_id,
            symbol="NVDA",
            quantity=10.0,
            direction="BUY",
            order_type="MARKET"
        )

    # 2. Route order with invalid PEP token signature must fail
    with pytest.raises(SignatureVerificationError, match="Invalid PEP transaction token"):
        adapter.route_order(
            execution_id=exec_id,
            symbol="NVDA",
            quantity=10.0,
            direction="BUY",
            order_type="MARKET",
            pep_token_signature="invalid_token_sig"
        )

    # 3. Route order with valid PEP token signature must pass
    valid_pep_token = sign_payload(keys["pep_priv"], exec_id)
    res = adapter.route_order(
        execution_id=exec_id,
        symbol="NVDA",
        quantity=10.0,
        direction="BUY",
        order_type="MARKET",
        pep_token_signature=valid_pep_token
    )
    assert res["status"] == "SENT"
    assert res["broker_order_ref"].startswith("ib_ord_")


# ----------------- Integration & File Repository Tests -----------------

def test_file_repositories_integration(keys, mock_ports) -> None:
    dec_port, gov_port = mock_ports
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize file repositories
        request_repo = FileExecutionRequestRepository(workspace_path=Path(temp_dir))
        routing_repo = FileRoutingRecordRepository(workspace_path=Path(temp_dir))
        fill_repo = FileFillRecordRepository(workspace_path=Path(temp_dir))

        pep_service = OrderPEPService(request_repo, dec_port, gov_port, keys["pep_priv"])
        adapter = InteractiveBrokersAdapter(keys["pep_pub"])
        routing_service = OrderRoutingService(routing_repo, request_repo, adapter, keys["pep_priv"])
        fill_service = FillService(fill_repo, routing_repo)
        projection_service = ExecutionStateProjectionService(request_repo, routing_repo, fill_repo)

        # Staging Parameters
        exec_id = generate_urn("record")
        dec_id = generate_urn("decision", context="cio")
        symbol = "urn:karsa:asset:ticker:nvda"
        quantity = 25.0

        cio_payload = f"{dec_id}|{symbol}|{quantity}"
        cio_signature = sign_payload(keys["cio_priv"], cio_payload)

        # Step 1: Stage and Validate
        token = pep_service.stage_and_validate(
            execution_id=exec_id,
            correlation_id=dec_id,
            causation_id=dec_id,
            symbol=symbol,
            quantity=quantity,
            direction="BUY",
            order_type="MARKET",
            price=100.0,
            cio_signature=cio_signature
        )
        assert token is not None
        assert projection_service.get_execution_state(exec_id) == ExecutionLifecycleState.PEP_VALIDATED

        # Verify request file exists
        req_loaded = request_repo.find_by_id(exec_id)
        assert req_loaded is not None
        assert req_loaded.quantity == 25.0

        # Step 2: Route Order
        route_id = routing_service.route_order(exec_id)
        assert route_id is not None
        assert projection_service.get_execution_state(exec_id) == ExecutionLifecycleState.ROUTED

        # Verify route file exists
        route_loaded = routing_repo.find_by_id(route_id)
        assert route_loaded is not None
        assert route_loaded.route_status == RouteStatus.SENT

        # Step 3: Record Fills
        fill_id = fill_service.record_fill(
            route_id=route_id,
            filled_quantity=25.0,
            filled_price=101.2,
            commission=1.00,
            slippage=0.05
        )
        assert fill_id is not None
        assert projection_service.get_execution_state(exec_id) == ExecutionLifecycleState.FILLED

        # Verify fill file exists
        fill_loaded = fill_repo.find_by_id(fill_id)
        assert fill_loaded is not None
        assert fill_loaded.filled_price == 101.2

        # Step 4: Validate Immutability constraints
        with pytest.raises(DatabaseImmutabilityError):
            request_repo.append(req_loaded)  # Append duplicate request should raise error

        with pytest.raises(DatabaseImmutabilityError):
            routing_repo.append(route_loaded)  # Append duplicate route should raise error

        with pytest.raises(DatabaseImmutabilityError):
            fill_repo.append(fill_loaded)  # Append duplicate fill should raise error


# ----------------- Replay & Audit Tests -----------------

def test_replay_determinism(keys, mock_ports) -> None:
    dec_port, gov_port = mock_ports
    req_repo = InMemoryExecutionRequestRepository()
    routing_repo = InMemoryRoutingRecordRepository()
    fill_repo = InMemoryFillRecordRepository()

    # Stage and execute an order in the past
    exec_id = generate_urn("record")
    dec_id = generate_urn("decision", context="cio")
    symbol = "NVDA"
    quantity = 10.0

    cio_payload = f"{dec_id}|{symbol}|{quantity}"
    cio_signature = sign_payload(keys["cio_priv"], cio_payload)

    pep_service = OrderPEPService(req_repo, dec_port, gov_port, keys["pep_priv"])
    token = pep_service.stage_and_validate(
        execution_id=exec_id,
        correlation_id=dec_id,
        causation_id=dec_id,
        symbol=symbol,
        quantity=quantity,
        direction="BUY",
        order_type="MARKET",
        price=100.0,
        cio_signature=cio_signature
    )

    adapter = InteractiveBrokersAdapter(keys["pep_pub"])
    routing_service = OrderRoutingService(routing_repo, req_repo, adapter, keys["pep_priv"])
    route_id = routing_service.route_order(exec_id)

    fill_service = FillService(fill_repo, routing_repo)
    fill_id = fill_service.record_fill(
        route_id=route_id,
        filled_quantity=10.0,
        filled_price=100.0,
        commission=1.0,
        slippage=0.0
    )

    # Replay simulation:
    # Given the fill record, we extract its details and trace causation/correlation links
    replayed_fill = fill_repo.find_by_id(fill_id)
    assert replayed_fill is not None

    replayed_route = routing_repo.find_by_id(replayed_fill.route_id)
    assert replayed_route is not None
    assert replayed_route.execution_id == exec_id

    replayed_request = req_repo.find_by_id(replayed_route.execution_id)
    assert replayed_request is not None
    assert replayed_request.correlation_id == dec_id

    # Re-verify original signatures to validate determinism
    is_cio_valid_again = dec_port.verify_decision_signature(
        decision_id=replayed_request.correlation_id,
        signature=replayed_request.cio_signature,
        order_details={
            "symbol": replayed_request.symbol,
            "quantity": replayed_request.quantity,
            "direction": replayed_request.direction,
            "order_type": replayed_request.order_type,
            "price": replayed_request.price
        }
    )
    assert is_cio_valid_again is True


# ----------------- Architecture Compliance Tests -----------------

def test_architecture_compliance() -> None:
    # 1. Verify Execution does not import any CIO or Decision Journal namespaces directly
    import sys
    for module in list(sys.modules.keys()):
        if module.startswith("karsa.execution."):
            imports = sys.modules[module].__dict__
            for imp_name, imp_val in imports.items():
                imp_module = getattr(imp_val, "__module__", "")
                assert not imp_module.startswith("karsa.cio"), f"Illegal import boundary in {module}: imports {imp_name} from CIO Engine"
                assert not imp_module.startswith("karsa.decision"), f"Illegal import boundary in {module}: imports {imp_name} from Decision Journal"

    # 2. Verify model parameters: execution owns fills, slippages, commissions, and staged orders.
    # It does not own holdings, NAV, exposures, or risk metrics.
    from karsa.execution.domain.models import ExecutionRequest, FillRecord
    fields_req = ExecutionRequest.__dataclass_fields__.keys()
    fields_fill = FillRecord.__dataclass_fields__.keys()

    prohibited_fields = ["holding", "holdings", "portfolio_state", "nav", "exposure", "risk_metrics", "policy"]
    for field in prohibited_fields:
        assert field not in fields_req, f"ExecutionRequest contains unauthorized portfolio field: {field}"
        assert field not in fields_fill, f"FillRecord contains unauthorized portfolio field: {field}"


# ----------------- FastAPI Router API Tests -----------------

@pytest.fixture
def api_app(keys, mock_ports) -> FastAPI:
    dec_port, gov_port = mock_ports
    request_repo = InMemoryExecutionRequestRepository()
    routing_repo = InMemoryRoutingRecordRepository()
    fill_repo = InMemoryFillRecordRepository()

    pep_service = OrderPEPService(request_repo, dec_port, gov_port, keys["pep_priv"])
    adapter = InteractiveBrokersAdapter(keys["pep_pub"])
    routing_service = OrderRoutingService(routing_repo, request_repo, adapter, keys["pep_priv"])
    fill_service = FillService(fill_repo, routing_repo)
    projection_service = ExecutionStateProjectionService(request_repo, routing_repo, fill_repo)

    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_pep_service] = lambda: pep_service
    app.dependency_overrides[get_routing_service] = lambda: routing_service
    app.dependency_overrides[get_fill_service] = lambda: fill_service
    app.dependency_overrides[get_projection_service] = lambda: projection_service

    return app


@pytest.fixture
def api_client(api_app) -> TestClient:
    return TestClient(api_app)


def test_api_stage_route_fill_lifecycle(api_client, keys) -> None:
    exec_id = generate_urn("record")
    dec_id = generate_urn("decision", context="cio")
    symbol = "NVDA"
    quantity = 15.0

    cio_payload = f"{dec_id}|{symbol}|{quantity}"
    cio_signature = sign_payload(keys["cio_priv"], cio_payload)

    # 1. POST Stage Order
    payload = {
        "execution_id": exec_id,
        "correlation_id": dec_id,
        "causation_id": dec_id,
        "symbol": symbol,
        "quantity": quantity,
        "direction": "BUY",
        "order_type": "MARKET",
        "price": 100.0,
        "cio_signature": cio_signature
    }
    resp = api_client.post("/execution/orders/stage", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["pep_status"] == "PEP_VALIDATED"
    assert data["pep_token_signature"] is not None

    # 2. GET projected state -> should be PEP_VALIDATED
    resp = api_client.get(f"/execution/orders/{exec_id}/state")
    assert resp.status_code == 200
    assert resp.json()["state"] == "PEP_VALIDATED"

    # 3. POST Route Order
    resp = api_client.post(f"/execution/orders/{exec_id}/route")
    assert resp.status_code == 200
    route_id = resp.json()["route_id"]
    assert route_id.startswith("urn:karsa:execution:route:")

    # GET projected state -> should be ROUTED
    resp = api_client.get(f"/execution/orders/{exec_id}/state")
    assert resp.status_code == 200
    assert resp.json()["state"] == "ROUTED"

    # 4. POST Fill Order
    fill_payload = {
        "route_id": route_id,
        "filled_quantity": quantity,
        "filled_price": 100.0,
        "commission": 1.0,
        "slippage": 0.0
    }
    resp = api_client.post("/execution/orders/fill", json=fill_payload)
    assert resp.status_code == 201
    assert resp.json()["status"] == "FILLED"

    # GET projected state -> should be FILLED
    resp = api_client.get(f"/execution/orders/{exec_id}/state")
    assert resp.status_code == 200
    assert resp.json()["state"] == "FILLED"
