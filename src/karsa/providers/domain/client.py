from abc import ABC, abstractmethod
from typing import Dict, Any, List

class ProviderClient(ABC):
    """Abstract interface for provider clients."""
    
    @abstractmethod
    def fetch_asset(self, asset_id: str) -> Dict[str, Any]:
        """Fetch raw data for a specific asset."""
        pass
        
    @abstractmethod
    def fetch_universe(self, universe_id: str) -> List[Dict[str, Any]]:
        """Fetch raw data for a universe of assets."""
        pass
        
    @abstractmethod
    def health_check(self) -> bool:
        """Perform a health check on the provider."""
        pass
