from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

@dataclass(frozen=True)
class PerformanceSnapshotPublishedEvent:
    target_id: str
    target_type: str
    metrics: Dict[str, Any]
    snapshot_timestamp: datetime

@dataclass(frozen=True)
class PerformanceDLQEvent:
    original_event: dict
    error_reason: str
    failed_at: datetime

