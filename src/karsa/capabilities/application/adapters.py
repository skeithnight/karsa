from abc import ABC, abstractmethod
from typing import Dict, Any, Callable
from karsa.capabilities.domain.models import CapabilityURN, ExecutionBudget

class ProviderAdapter(ABC):
    @abstractmethod
    def execute_capability(
        self,
        urn: CapabilityURN,
        input_payload: Dict[str, Any],
        budget: ExecutionBudget
    ) -> Dict[str, Any]:
        """Physically execute the capability and return the output dictionary."""
        pass

class MockProviderAdapter(ProviderAdapter):
    def __init__(self):
        self._mocks: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def register_mock(self, urn_str: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self._mocks[urn_str] = handler

    def execute_capability(
        self,
        urn: CapabilityURN,
        input_payload: Dict[str, Any],
        budget: ExecutionBudget
    ) -> Dict[str, Any]:
        urn_str = urn.to_string()
        if urn_str in self._mocks:
            return self._mocks[urn_str](input_payload)
            
        # Default behavior: Echo inputs or return a default placeholder
        return {
            "stdout": "Mock execution completed successfully.",
            "stderr": "",
            "exit_code": 0,
            "echo_input": input_payload
        }
