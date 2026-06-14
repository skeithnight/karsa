from typing import Optional, Callable, Dict, Any
from datetime import datetime, timezone
import uuid
from cryptography.hazmat.primitives.asymmetric import ed25519

from karsa.execution.application.ports import (
    DecisionAuthorizationPort, GovernanceAuthorizationPort, BrokerAdapterPort
)
from karsa.execution.domain.exceptions import (
    SignatureVerificationError, PolicyLimitExceededError, BrokerRoutingError,
    ExecutionNotFoundError
)
from karsa.execution.domain.models import (
    ExecutionRequest, RoutingRecord, FillRecord, PEPValidationStatus, RouteStatus,
    ExecutionLifecycleState, generate_urn
)
from karsa.execution.domain.events import (
    OrderStagedEvent, OrderValidatedEvent, OrderRoutedEvent, OrderFilledEvent,
    OrderRejectedEvent, ExecutionIncidentEvent
)
from karsa.execution.domain.security import sign_payload


class OrderPEPService:
    """Policy Enforcement Point service coordinating order staging and dual-signature verification."""

    def __init__(
        self,
        request_repo: Any,
        decision_auth_port: DecisionAuthorizationPort,
        gov_auth_port: GovernanceAuthorizationPort,
        pep_private_key: ed25519.Ed25519PrivateKey,
        event_publisher: Optional[Callable[[Any], None]] = None,
    ) -> None:
        self.request_repo = request_repo
        self.decision_auth_port = decision_auth_port
        self.gov_auth_port = gov_auth_port
        self.pep_private_key = pep_private_key
        self.event_publisher = event_publisher

    def stage_and_validate(
        self,
        execution_id: str,
        correlation_id: str,
        causation_id: str,
        symbol: str,
        quantity: float,
        direction: str,
        order_type: str,
        price: Optional[float],
        cio_signature: str,
        gov_exception_id: Optional[str] = None,
        gov_exception_signature: Optional[str] = None,
    ) -> str:
        """Stages an order, performs pre-trade PEP validations, and writes outcomes to the ledger.

        Returns:
            The generated PEP validation signature token string if validated successfully.
        """
        # 1. Publish OrderStagedEvent
        staged_event = OrderStagedEvent(
            correlation_id=correlation_id,
            causation_id=causation_id,
            execution_id=execution_id,
            symbol=symbol,
            quantity=quantity,
            direction=direction,
            order_type=order_type,
            price=price,
        )
        if self.event_publisher:
            self.event_publisher(staged_event)

        order_details = {
            "symbol": symbol,
            "quantity": quantity,
            "direction": direction,
            "order_type": order_type,
            "price": price,
        }

        # 2. Verify CIO Decision Signature
        # Note: correlation_id represents the decision URN (authorizing factor)
        is_cio_valid = self.decision_auth_port.verify_decision_signature(
            decision_id=correlation_id,
            signature=cio_signature,
            order_details=order_details
        )
        if not is_cio_valid:
            # Stage rejection in repo
            request = ExecutionRequest(
                execution_id=execution_id,
                correlation_id=correlation_id,
                causation_id=causation_id,
                symbol=symbol,
                quantity=quantity,
                direction=direction,
                order_type=order_type,
                price=price,
                cio_signature=cio_signature,
                gov_exception_id=gov_exception_id,
                gov_exception_signature=gov_exception_signature,
                pep_status=PEPValidationStatus.REJECTED,
                rejection_reason="Invalid CIO Decision signature."
            )
            self.request_repo.append(request)
            if self.event_publisher:
                self.event_publisher(OrderRejectedEvent(
                    correlation_id=correlation_id,
                    causation_id=staged_event.event_id,
                    execution_id=execution_id,
                    reason="Invalid CIO Decision signature."
                ))
            raise SignatureVerificationError("Invalid CIO Decision signature.")

        # 3. Check compliance policy limits
        within_limits = self.gov_auth_port.check_policy_limits(order_details)
        if not within_limits:
            # Requires Governance Exception signature
            if not gov_exception_id or not gov_exception_signature:
                request = ExecutionRequest(
                    execution_id=execution_id,
                    correlation_id=correlation_id,
                    causation_id=causation_id,
                    symbol=symbol,
                    quantity=quantity,
                    direction=direction,
                    order_type=order_type,
                    price=price,
                    cio_signature=cio_signature,
                    gov_exception_id=gov_exception_id,
                    gov_exception_signature=gov_exception_signature,
                    pep_status=PEPValidationStatus.REJECTED,
                    rejection_reason="Compliance limits exceeded; Governance Exception token is missing."
                )
                self.request_repo.append(request)
                if self.event_publisher:
                    self.event_publisher(OrderRejectedEvent(
                        correlation_id=correlation_id,
                        causation_id=staged_event.event_id,
                        execution_id=execution_id,
                        reason="Compliance limits exceeded; Governance Exception token is missing."
                    ))
                raise PolicyLimitExceededError("Compliance limits exceeded; Governance Exception token is missing.")

            # Validate exception token signature
            is_exception_valid = self.gov_auth_port.verify_governance_exception(
                exception_id=gov_exception_id,
                signature=gov_exception_signature,
                order_details=order_details
            )
            if not is_exception_valid:
                request = ExecutionRequest(
                    execution_id=execution_id,
                    correlation_id=correlation_id,
                    causation_id=causation_id,
                    symbol=symbol,
                    quantity=quantity,
                    direction=direction,
                    order_type=order_type,
                    price=price,
                    cio_signature=cio_signature,
                    gov_exception_id=gov_exception_id,
                    gov_exception_signature=gov_exception_signature,
                    pep_status=PEPValidationStatus.REJECTED,
                    rejection_reason="Invalid Governance Exception signature."
                )
                self.request_repo.append(request)
                if self.event_publisher:
                    self.event_publisher(OrderRejectedEvent(
                        correlation_id=correlation_id,
                        causation_id=staged_event.event_id,
                        execution_id=execution_id,
                        reason="Invalid Governance Exception signature."
                    ))
                raise SignatureVerificationError("Invalid Governance Exception signature.")

        # 4. Generate PEP Validation Signature Token
        pep_token = sign_payload(self.pep_private_key, execution_id)

        # 5. Append Approved request to the ledger
        request = ExecutionRequest(
            execution_id=execution_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
            symbol=symbol,
            quantity=quantity,
            direction=direction,
            order_type=order_type,
            price=price,
            cio_signature=cio_signature,
            gov_exception_id=gov_exception_id,
            gov_exception_signature=gov_exception_signature,
            pep_status=PEPValidationStatus.PEP_VALIDATED
        )
        self.request_repo.append(request)

        # 6. Publish OrderValidatedEvent
        if self.event_publisher:
            self.event_publisher(OrderValidatedEvent(
                correlation_id=correlation_id,
                causation_id=staged_event.event_id,
                execution_id=execution_id
            ))

        return pep_token


class OrderRoutingService:
    """Service coordinates routing validated orders to vendor adapters."""

    def __init__(
        self,
        routing_repo: Any,
        request_repo: Any,
        broker_adapter: BrokerAdapterPort,
        pep_private_key: ed25519.Ed25519PrivateKey,
        event_publisher: Optional[Callable[[Any], None]] = None,
    ) -> None:
        self.routing_repo = routing_repo
        self.request_repo = request_repo
        self.broker_adapter = broker_adapter
        self.pep_private_key = pep_private_key
        self.event_publisher = event_publisher

    def route_order(self, execution_id: str) -> str:
        """Retrieves validated requests, generates PEP token, and routes to broker adapter."""
        request = self.request_repo.find_by_id(execution_id)
        if not request:
            raise ExecutionNotFoundError(f"Execution request {execution_id} not found.")

        if request.pep_status != PEPValidationStatus.PEP_VALIDATED:
            raise ValueError(f"Cannot route execution request {execution_id} in status {request.pep_status.value}.")

        # Generate fresh token
        pep_token = sign_payload(self.pep_private_key, execution_id)

        route_id = generate_urn("route")

        try:
            # Route to broker adapter
            route_res = self.broker_adapter.route_order(
                execution_id=execution_id,
                symbol=request.symbol,
                quantity=request.quantity,
                direction=request.direction,
                order_type=request.order_type,
                price=request.price,
                pep_token_signature=pep_token
            )

            status = RouteStatus(route_res["status"])
            broker_order_ref = route_res.get("broker_order_ref")

            record = RoutingRecord(
                route_id=route_id,
                execution_id=execution_id,
                broker_id=self.broker_adapter.broker_id,
                broker_order_ref=broker_order_ref,
                route_status=status
            )
            self.routing_repo.append(record)

            if status == RouteStatus.SENT:
                if self.event_publisher:
                    self.event_publisher(OrderRoutedEvent(
                        correlation_id=request.correlation_id,
                        causation_id=execution_id,
                        execution_id=execution_id,
                        broker_id=self.broker_adapter.broker_id,
                        broker_order_ref=broker_order_ref or ""
                    ))
            else:
                reason = route_res.get("error_message") or "Broker routing rejected."
                if self.event_publisher:
                    self.event_publisher(OrderRejectedEvent(
                        correlation_id=request.correlation_id,
                        causation_id=execution_id,
                        execution_id=execution_id,
                        reason=reason
                    ))
                raise BrokerRoutingError(reason)

        except Exception as e:
            if not isinstance(e, BrokerRoutingError):
                # Save routing rejection record
                record = RoutingRecord(
                    route_id=route_id,
                    execution_id=execution_id,
                    broker_id=self.broker_adapter.broker_id,
                    broker_order_ref=None,
                    route_status=RouteStatus.REJECTED
                )
                self.routing_repo.append(record)

                if self.event_publisher:
                    self.event_publisher(ExecutionIncidentEvent(
                        correlation_id=request.correlation_id,
                        causation_id=execution_id,
                        execution_id=execution_id,
                        incident_type="BROKER_ROUTING_EXCEPTION",
                        details=str(e)
                    ))
                    self.event_publisher(OrderRejectedEvent(
                        correlation_id=request.correlation_id,
                        causation_id=execution_id,
                        execution_id=execution_id,
                        reason=f"Broker exception: {str(e)}"
                    ))
                raise BrokerRoutingError(f"Broker routing failed with exception: {e}")
            raise e

        return route_id


class FillService:
    """Service handles recording fills and mapping transactions costs."""

    def __init__(
        self,
        fill_repo: Any,
        routing_repo: Any,
        event_publisher: Optional[Callable[[Any], None]] = None,
    ) -> None:
        self.fill_repo = fill_repo
        self.routing_repo = routing_repo
        self.event_publisher = event_publisher

    def record_fill(
        self,
        route_id: str,
        filled_quantity: float,
        filled_price: float,
        commission: float,
        slippage: float,
        correlation_id: str = "",
    ) -> str:
        """Records executing fills received from broker and emits OrderFilledEvent."""
        route = self.routing_repo.find_by_id(route_id)
        if not route:
            raise ExecutionNotFoundError(f"Routing record {route_id} not found.")

        fill_id = generate_urn("fill")
        record = FillRecord(
            fill_id=fill_id,
            route_id=route_id,
            filled_quantity=filled_quantity,
            filled_price=filled_price,
            commission=commission,
            slippage=slippage
        )
        self.fill_repo.append(record)

        if self.event_publisher:
            self.event_publisher(OrderFilledEvent(
                correlation_id=correlation_id or route_id,
                causation_id=route_id,
                execution_id=route.execution_id,
                filled_quantity=filled_quantity,
                filled_price=filled_price,
                commission=commission,
                slippage=slippage
            ))

        return fill_id


class ExecutionStateProjectionService:
    """Reconstructs the active state of an execution request lock-free from append-only ledgers."""

    def __init__(self, request_repo: Any, routing_repo: Any, fill_repo: Any) -> None:
        self.request_repo = request_repo
        self.routing_repo = routing_repo
        self.fill_repo = fill_repo

    def get_execution_state(self, execution_id: str) -> ExecutionLifecycleState:
        """Walks the append-only logs to determine the logical state of an execution."""
        request = self.request_repo.find_by_id(execution_id)
        if not request:
            raise ExecutionNotFoundError(f"Execution request {execution_id} not found.")

        if request.pep_status == PEPValidationStatus.REJECTED:
            return ExecutionLifecycleState.REJECTED

        if request.pep_status == PEPValidationStatus.STAGED:
            return ExecutionLifecycleState.STAGED

        # Find routing records
        routes = self.routing_repo.find_by_execution_id(execution_id)
        if not routes:
            return ExecutionLifecycleState.PEP_VALIDATED

        # Evaluate routes
        for r in routes:
            if r.route_status == RouteStatus.REJECTED:
                return ExecutionLifecycleState.REJECTED
            elif r.route_status == RouteStatus.SENT:
                # Check for fills
                fills = self.fill_repo.find_by_route_id(r.route_id)
                if fills:
                    return ExecutionLifecycleState.FILLED
                return ExecutionLifecycleState.ROUTED

        return ExecutionLifecycleState.PEP_VALIDATED
