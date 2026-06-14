from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

class EventPublisherPort(ABC):
    @abstractmethod
    def publish(self, event: Any) -> None:
        """Publishes domain events to the shared event bus."""
        pass

class ReturnsDataPort(ABC):
    @abstractmethod
    def get_historical_returns(self, asset_urns: List[str], start_date: datetime, end_date: datetime) -> Dict[str, List[float]]:
        """Fetches historical returns list per asset for parameter estimation."""
        pass

class RegimeStatePort(ABC):
    @abstractmethod
    def get_active_regime_multiplier(self) -> Dict[str, Any]:
        """Fetches active macro regime and its corresponding volatility scaling factor."""
        pass

class ObjectStorePort(ABC):
    @abstractmethod
    def save_matrix(self, matrix_urn: str, data: List[List[float]]) -> None:
        """Saves a large covariance matrix to the object store."""
        pass

    @abstractmethod
    def get_matrix(self, matrix_urn: str) -> List[List[float]]:
        """Retrieves a covariance matrix from the object store."""
        pass
