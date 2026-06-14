from typing import Optional, Dict, Any
import uuid
from karsa.execution.application.ports import BrokerAdapterPort
from karsa.execution.domain.exceptions import SignatureVerificationError
from karsa.execution.domain.security import verify_payload_signature
from cryptography.hazmat.primitives.asymmetric import ed25519


class InteractiveBrokersAdapter(BrokerAdapterPort):
    """Mock adapter simulating order routing to Interactive Brokers."""

    def __init__(self, pep_public_key: ed25519.Ed25519PublicKey) -> None:
        """Initializes the adapter with the PEP public key to verify tokens.

        Args:
            pep_public_key: The Ed25519 public key of the PEP.
        """
        self.pep_public_key = pep_public_key
        self.broker_id = "interactive_brokers_v2"
        self._routed_orders: list = []

    def route_order(
        self,
        execution_id: str,
        symbol: str,
        quantity: float,
        direction: str,
        order_type: str,
        price: Optional[float] = None,
        pep_token_signature: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatches an order to IB after verifying the PEP validation token signature."""
        if not pep_token_signature:
            raise SignatureVerificationError("Bypass detected: Outbound order missing PEP transaction token.")

        # The payload to verify is the execution_id
        is_valid = verify_payload_signature(self.pep_public_key, execution_id, pep_token_signature)
        if not is_valid:
            raise SignatureVerificationError("Bypass detected: Invalid PEP transaction token.")

        # Simulate broker routing success
        broker_order_ref = f"ib_ord_{uuid.uuid4().hex[:8]}"
        route_details = {
            "broker_id": self.broker_id,
            "broker_order_ref": broker_order_ref,
            "status": "SENT",
        }
        self._routed_orders.append((execution_id, route_details))
        return route_details
