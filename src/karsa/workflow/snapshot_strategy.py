from dataclasses import dataclass
from karsa.domain.models import WorkflowSnapshot
from karsa.domain.persistence import EventJournalRepository

@dataclass
class SnapshotStrategyConfig:
    event_count_threshold: int = 100
    journal_size_threshold_mb: float = 5.0

class SnapshotStrategy:
    def __init__(self, config: SnapshotStrategyConfig, event_repo: EventJournalRepository):
        self.config = config
        self.event_repo = event_repo
        
    def should_snapshot(self, snapshot: WorkflowSnapshot, new_event_count: int) -> bool:
        if new_event_count >= self.config.event_count_threshold:
            return True
            
        path = self.event_repo._get_path(snapshot.workflow_id)
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb >= self.config.journal_size_threshold_mb:
                return True
                
        return False
