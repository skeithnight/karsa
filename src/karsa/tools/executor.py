import subprocess
from pathlib import Path

class ToolExecutor:
    def __init__(self, timeout: int = 30, max_output_chars: int = 5000):
        self.timeout = timeout
        self.max_output_chars = max_output_chars

    def run_pytest(self, cwd: Path) -> str:
        return self._run_command(["python3", "-m", "pytest", "-v"], cwd)

    def run_python(self, script_name: str, cwd: Path) -> str:
        return self._run_command(["python3", script_name], cwd)

    def _run_command(self, cmd: list, cwd: Path) -> str:
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            output = f"Exit code: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            output = f"Command timed out after {self.timeout} seconds"
        except Exception as e:
            output = f"Error running command: {e}"
            
        if len(output) > self.max_output_chars:
            output = output[-self.max_output_chars:] + "\n... (truncated)"
            
        return output
