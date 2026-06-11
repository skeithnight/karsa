from pathlib import Path
import difflib

class ArtifactDiffTracker:
    def __init__(self, workspace_dir: Path):
        self.diffs_dir = workspace_dir / ".karsa" / "artifact_diffs"
        self.diffs_dir.mkdir(parents=True, exist_ok=True)

    def generate_diff_summary(self, old_content: str, new_content: str, filename: str, cycle: int):
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = list(difflib.unified_diff(old_lines, new_lines, fromfile=f"{filename} (Original)", tofile=f"{filename} (Revised)"))
        
        diff_file = self.diffs_dir / f"DIFF_{cycle:03d}.md"
        
        mode = "a" if diff_file.exists() else "w"
        with open(diff_file, mode) as f:
            f.write(f"\n### {filename}\n```diff\n")
            f.writelines(diff)
            f.write("```\n")
