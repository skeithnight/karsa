import subprocess
from pathlib import Path

class GitManager:
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir

    def run_command(self, *args) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            # Could log or handle specific errors here
            return ""

    def initialize(self):
        if not (self.workspace_dir / ".git").exists():
            self.run_command("init")

    def commit_state(self, message: str):
        self.run_command("add", ".")
        status = self.run_command("status", "--porcelain")
        if status:
            self.run_command("commit", "-m", message)

    def tag_approval(self, tag_name: str, message: str):
        self.run_command("tag", "-a", tag_name, "-m", message)
