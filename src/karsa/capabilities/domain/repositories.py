from abc import ABC, abstractmethod
from typing import Optional, List
from karsa.capabilities.domain.models import CapabilityDefinition, CapabilityExecution, CapabilityURN

class CapabilityDefinitionRepository(ABC):
    @abstractmethod
    def save(self, definition: CapabilityDefinition) -> None:
        """Persist a CapabilityDefinition aggregate."""
        pass

    @abstractmethod
    def find_by_id(self, capability_id: str) -> Optional[CapabilityDefinition]:
        """Retrieve a CapabilityDefinition by its immutable capability_id."""
        pass

    @abstractmethod
    def find_by_urn(self, urn: CapabilityURN) -> Optional[CapabilityDefinition]:
        """Retrieve a CapabilityDefinition by its logical URN."""
        pass

    @abstractmethod
    def find_by_family(self, capability_family_id: str) -> List[CapabilityDefinition]:
        """Retrieve all versions of a capability definition family by family ID."""
        pass

    @abstractmethod
    def find_active(self) -> List[CapabilityDefinition]:
        """Retrieve all active capability definitions."""
        pass

class CapabilityExecutionRepository(ABC):
    @abstractmethod
    def save(self, execution: CapabilityExecution) -> None:
        """Persist a CapabilityExecution aggregate."""
        pass

    @abstractmethod
    def find_by_id(self, execution_id: str) -> Optional[CapabilityExecution]:
        """Retrieve a CapabilityExecution by its unique execution_id."""
        pass
