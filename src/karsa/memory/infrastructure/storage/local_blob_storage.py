import json
import os
from typing import Dict, Any, Optional
from karsa.memory.domain.repository.blob_storage import BlobStorage

class LocalBlobStorage(BlobStorage):
    def __init__(self, base_path: str):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)
        
    def store_blob(self, namespace: str, payload_hash: str, payload: Dict[str, Any]) -> str:
        """Stores a JSON payload to the local filesystem and returns a URI."""
        ns_path = os.path.join(self.base_path, namespace)
        os.makedirs(ns_path, exist_ok=True)
        
        file_path = os.path.join(ns_path, f"{payload_hash}.json")
        with open(file_path, "w") as f:
            json.dump(payload, f)
            
        return f"file://{file_path}"
        
    def retrieve_blob(self, blob_uri: str) -> Optional[Dict[str, Any]]:
        """Retrieves a JSON payload from the local filesystem."""
        if not blob_uri.startswith("file://"):
            return None
            
        file_path = blob_uri[7:]
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, "r") as f:
            return json.load(f)

    def retrieve_by_hash(self, namespace: str, payload_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieves a JSON payload by its namespace and hash."""
        file_path = os.path.join(self.base_path, namespace, f"{payload_hash}.json")
        return self.retrieve_blob(f"file://{file_path}")
