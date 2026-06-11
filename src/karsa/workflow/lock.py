import json
import time
from pathlib import Path
from typing import Optional

class WorkflowLockedError(Exception):
    pass

class WorkflowLockManager:
    def __init__(self, workspace_path: Path, ttl_seconds: int = 300):
        self.workspace_path = workspace_path
        self.ttl_seconds = ttl_seconds
        
    def _get_path(self, workflow_id: str) -> Path:
        return self.workspace_path / ".karsa" / "workflows" / workflow_id / "lock.json"
        
    def acquire(self, workflow_id: str, process_id: str):
        path = self._get_path(workflow_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        now = time.time()
        
        if path.exists():
            with open(path, "r") as f:
                try:
                    data = json.load(f)
                    expires_at = data.get("expires_at", 0)
                    if now < expires_at:
                        raise WorkflowLockedError(f"Workflow {workflow_id} is currently locked by process {data.get('process_id')}")
                except json.JSONDecodeError:
                    pass # Corrupted lock, overwrite it
                    
        lock_data = {
            "workflow_id": workflow_id,
            "process_id": process_id,
            "acquired_at": now,
            "expires_at": now + self.ttl_seconds
        }
        
        with open(path, "w") as f:
            json.dump(lock_data, f, indent=2)
            
    def release(self, workflow_id: str, process_id: str):
        path = self._get_path(workflow_id)
        if not path.exists():
            return
            
        with open(path, "r") as f:
            try:
                data = json.load(f)
                if data.get("process_id") == process_id:
                    path.unlink()
            except json.JSONDecodeError:
                path.unlink() # Corrupted, just remove
