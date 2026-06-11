import os
from pathlib import Path

class ArtifactManager:
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.docs_dir = self.workspace_dir / "docs"
        self.src_dir = self.workspace_dir / "src"

    def initialize(self):
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.src_dir.mkdir(parents=True, exist_ok=True)

    def write_artifact(self, relative_path: str, content: str):
        filepath = self.workspace_dir / relative_path
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)

    def read_artifact(self, relative_path: str) -> str:
        filepath = self.workspace_dir / relative_path
        if not filepath.exists():
            return ""
        with open(filepath, "r") as f:
            return f.read()
