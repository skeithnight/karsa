from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class DecisionAuthorizationPort(ABC):
    """Port for verifying the CIO Decision authorization signature."""

    @abstractmethod
    def verify_decision_signature(self, decision_id: str, signature: str, order_details: Dict[str, Any]) -> bool:
        """Verifies the cryptographic signature of the CIO Decision authorizing this execution request.

        Args:
            decision_id: The URN of the CIO decision.
            signature: The cryptographic signature.
            order_details: Dict containing order details (symbol, quantity, direction, etc.) to verify against.

        Returns:
            True if signature is valid, False otherwise.
        """
        pass


class GovernanceAuthorizationPort(ABC):
    """Port for verifying governance compliance limits and exceptions."""

    @abstractmethod
    def check_policy_limits(self, order_details: Dict[str, Any]) -> bool:
        """Checks if the staged order conforms to default compliance policy limits.

        Args:
            order_details: Dict containing order details.

        Returns:
            True if the order is within default limits, False if limits are exceeded.
        """
        pass

    @abstractmethod
    def verify_governance_exception(self, exception_id: str, signature: str, order_details: Dict[str, Any]) -> bool:
        """Verifies the cryptographic signature of the Governance Exception token.

        Args:
            exception_id: The URN of the exception token.
            signature: The cryptographic signature.
            order_details: Dict containing order details.

        Returns:
            True if the exception signature is valid, False otherwise.
        """
        pass


class BrokerAdapterPort(ABC):
    """Port for communicating with live or simulated broker venues."""

    @abstractmethod
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
        """Dispatches an approved execution request to the broker.

        Args:
            execution_id: The URN of the execution request.
            symbol: Ticker symbol or asset URN.
            quantity: Position volume.
            direction: BUY or SELL.
            order_type: MARKET or LIMIT.
            price: Optional limit price.
            pep_token_signature: Base64 string of the PEP's transaction token signature.

        Returns:
            Dict containing:
                - broker_id: Identifier of the broker adapter.
                - broker_order_ref: Unique external broker order reference.
                - status: RouteStatus string (SENT or REJECTED).
                - error_message: Optional string if status is REJECTED.
        """
        pass
