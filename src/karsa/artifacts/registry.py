import hashlib
import os
import shutil
from pathlib import Path
from typing import Optional

class ArtifactRegistry:
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.artifacts_dir = self.workspace_path / ".karsa" / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        
    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
        
    def store_versioned(self, content: str) -> str:
        version_hash = self._compute_hash(content)
        path = self.artifacts_dir / f"{version_hash}.md"
        
        # Staging atomicity: write to tmp then rename
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            f.write(content)
        os.rename(tmp_path, path)
        
        return version_hash
        
    def get_versioned(self, version_hash: str) -> Optional[str]:
        path = self.artifacts_dir / f"{version_hash}.md"
        if not path.exists():
            return None
        with open(path, "r") as f:
            return f.read()

    def get_versioned_path(self, version_hash: str) -> Path:
        return self.artifacts_dir / f"{version_hash}.md"

    def hash_live_file(self, target_path: str) -> Optional[str]:
        path = self.workspace_path / target_path
        if not path.exists():
            return None
        with open(path, "r") as f:
            content = f.read()
            return self._compute_hash(content)
