from pathlib import Path
from datetime import datetime, timezone
import json

def get_iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')

class TraceLogger:
    def __init__(self, workspace_dir: Path):
        self.log_file = workspace_dir / ".karsa" / "trace.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_event(self, event_name: str):
        timestamp = get_iso_timestamp()
        log_entry = f"{timestamp}\n{event_name}\n\n"
        with open(self.log_file, "a") as f:
            f.write(log_entry)
