from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

class BlobStorage(ABC):
    @abstractmethod
    def store_blob(self, namespace: str, payload_hash: str, payload: Dict[str, Any]) -> str:
        """Stores a JSON payload and returns the blob URI."""
        pass
        
    @abstractmethod
    def retrieve_blob(self, blob_uri: str) -> Optional[Dict[str, Any]]:
        """Retrieves a JSON payload by its URI."""
        pass

    @abstractmethod
    def retrieve_by_hash(self, namespace: str, payload_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieves a JSON payload by its namespace and hash."""
        pass
