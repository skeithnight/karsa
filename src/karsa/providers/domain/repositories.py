from abc import ABC, abstractmethod
from typing import List, Optional
from karsa.providers.domain.models import ProviderDefinition, ProviderHealthState, ProviderURN

class ProviderDefinitionRepository(ABC):
    @abstractmethod
    def save(self, provider: ProviderDefinition) -> None:
        pass

    @abstractmethod
    def find_by_id(self, provider_id: str) -> Optional[ProviderDefinition]:
        pass

    @abstractmethod
    def find_by_urn(self, urn: ProviderURN) -> Optional[ProviderDefinition]:
        pass

    @abstractmethod
    def find_active_for_capability(self, capability_urn: str) -> List[ProviderDefinition]:
        pass

class ProviderHealthStateRepository(ABC):
    @abstractmethod
    def save(self, health: ProviderHealthState) -> None:
        pass

    @abstractmethod
    def find_by_provider_id(self, provider_id: str) -> Optional[ProviderHealthState]:
        pass
