"""Connector Factory — registry pattern for data providers.

Sprint-51: BaseConnector composes with existing ProviderClient.
Concrete connectors (Polygon, Finnhub) are registered via decorator.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Type, Optional
import logging

from karsa.providers.domain.client import ProviderClient

logger = logging.getLogger(__name__)

# Global registry: provider_name -> connector class
CONNECTOR_REGISTRY: Dict[str, Type["BaseConnector"]] = {}


def register_connector(provider_name: str):
    """Decorator to register a connector class for a provider name."""
    def decorator(cls: Type["BaseConnector"]):
        CONNECTOR_REGISTRY[provider_name] = cls
        return cls
    return decorator


class BaseConnector(ABC):
    """Abstract base for data bridge connectors.

    Composes with the existing ProviderClient interface, adding
    lifecycle management (start/stop) for streaming connectors.
    """

    def __init__(
        self,
        provider_id: str,
        config: Dict[str, Any],
        credentials: Dict[str, str],
    ):
        self.provider_id = provider_id
        self.config = config
        self.credentials = credentials
        self._running = False

    @abstractmethod
    async def start(self) -> None:
        """Initialize the connector (open WebSocket, start polling, etc.)."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully shut down the connector."""
        pass

    async def reset(self) -> None:
        """Reset internal state for supervised restart.

        Override in subclasses that maintain internal queues or tasks.
        Default implementation is a no-op.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the connector is healthy."""
        pass

    @property
    def is_running(self) -> bool:
        return self._running


class ConnectorFactory:
    """Factory for creating connector instances from provider config."""

    @staticmethod
    def create(
        provider_name: str,
        provider_id: str,
        config: Dict[str, Any],
        credentials: Dict[str, str],
        dead_letter_repo=None,
    ) -> BaseConnector:
        """Create a connector instance for the given provider name.

        Args:
            provider_name: Registry key (e.g., 'polygon', 'finnhub').
            provider_id: UUID of the data_providers row.
            config: JSONB config from provider_configurations.
            credentials: Decrypted API key/secret.
            dead_letter_repo: Optional DeadLetterRepository for normalization failures.

        Returns:
            BaseConnector instance.

        Raises:
            ValueError: If no connector is registered for the provider name.
        """
        connector_cls = CONNECTOR_REGISTRY.get(provider_name)
        if not connector_cls:
            available = list(CONNECTOR_REGISTRY.keys())
            raise ValueError(
                f"No connector registered for '{provider_name}'. "
                f"Available: {available}"
            )
        logger.info(f"Creating connector for {provider_name} (id={provider_id})")

        # Check if connector accepts dead_letter_repo parameter
        import inspect
        sig = inspect.signature(connector_cls.__init__)
        if "dead_letter_repo" in sig.parameters:
            return connector_cls(
                provider_id=provider_id,
                config=config,
                credentials=credentials,
                dead_letter_repo=dead_letter_repo,
            )
        return connector_cls(
            provider_id=provider_id,
            config=config,
            credentials=credentials,
        )

    @staticmethod
    def list_registered() -> list:
        """List all registered connector names."""
        return list(CONNECTOR_REGISTRY.keys())
