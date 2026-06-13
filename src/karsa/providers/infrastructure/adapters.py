from abc import ABC, abstractmethod
from typing import Dict, Any
from karsa.providers.domain.models import ProviderURN

class BaseProviderAdapter(ABC):
    @abstractmethod
    def execute(self, prompt: str, **kwargs) -> str:
        """Execute the logical capability invocation against the physical model."""
        pass

    @abstractmethod
    def get_provider_urn(self) -> ProviderURN:
        """Get the URN of the provider backend."""
        pass


class MockProviderAdapter(BaseProviderAdapter):
    def __init__(self, provider_urn: ProviderURN):
        self.provider_urn = provider_urn

    def execute(self, prompt: str, **kwargs) -> str:
        # Generate a mock response string including the provider URN details
        return f"[Mock Response from {self.provider_urn.to_string()}] prompt: {prompt}"

    def get_provider_urn(self) -> ProviderURN:
        return self.provider_urn


class AdapterRegistry:
    def __init__(self):
        self._adapters: Dict[str, BaseProviderAdapter] = {}

    def register(self, provider_id: str, adapter: BaseProviderAdapter) -> None:
        self._adapters[provider_id] = adapter

    def get_adapter(self, provider_id: str) -> BaseProviderAdapter:
        if provider_id not in self._adapters:
            raise ValueError(f"No adapter registered for provider ID: {provider_id}")
        return self._adapters[provider_id]
