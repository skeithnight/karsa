import os
from pathlib import Path

class ArtifactManager:
    def __init__(self, workspace_dir: Path, obs_manager=None):
        self.workspace = workspace_dir
        self.obs = obs_manager
        self.docs_dir = self.workspace / "docs"
        self.src_dir = self.workspace / "src"

    def initialize(self):
        # Create standard directory structure
        directories = [
            "docs/vision",
            "docs/architecture",
            "docs/implementation",
            "docs/reviews",
            "docs/revisions",
            "src",
            "tests"
        ]
        
        for d in directories:
            (self.workspace / d).mkdir(parents=True, exist_ok=True)

    def write_artifact(self, rel_path: str, content: str):
        file_path = self.workspace / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)
        if self.obs:
            self.obs.log_trace("ArtifactWritten")

    def read_artifact(self, relative_path: str) -> str:
        filepath = self.workspace / relative_path
        if not filepath.exists():
            return ""
        with open(filepath, "r") as f:
            return f.read()
